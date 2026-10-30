import hmac
import hashlib
import re
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic
from urllib.parse import unquote, urlsplit

from fastapi import Request, Response

from .errors import ApiError

ACCESS = 'shop_access'
REFRESH = 'shop_refresh'
CSRF = 'shop_csrf'
AUTH_PATH = '/api/v1/auth'


def safe_next(value: str) -> str:
    if len(value) > 2048:
        return '/'
    decoded = value
    for _ in range(4):
        decoded = unquote(decoded)
    if any(ord(c) < 32 or ord(c) == 127 for c in decoded) or '\\' in decoded:
        return '/'
    try:
        parts = urlsplit(decoded)
    except ValueError:
        return '/'
    if parts.scheme or parts.netloc or decoded.startswith('//') or parts.fragment:
        return '/'
    allowed = r'/(?:|cart|checkout|mypage(?:/edit|/orders(?:/[0-9a-fA-F-]{36})?)?|products/[0-9a-fA-F-]{36})'
    if not re.fullmatch(allowed, parts.path):
        return '/'
    # Preserve the original encoded query; never return an absolute/external URL.
    return value


def csrf_error(request: Request):
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    origin = request.headers.get('origin')
    if origin and origin != request.app.state.settings.app_origin:
        return ApiError(403, 'CSRF_FAILED', '요청 출처가 일치하지 않습니다.')
    cookie = request.cookies.get(CSRF, '')
    header = request.headers.get('x-csrf-token', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{40,80}', cookie) or not re.fullmatch(r'[A-Za-z0-9_-]{40,80}', header) or not hmac.compare_digest(cookie, header):
        return ApiError(403, 'CSRF_FAILED', '보안 토큰을 새로 발급받아 주세요.')
    if request.headers.get('content-type', '').split(';')[0].lower() != 'application/json':
        return ApiError(415, 'JSON_REQUIRED', 'Content-Type: application/json을 사용해 주세요.')
    return None


def set_session(response: Response, session: dict, settings):
    seconds = settings.session_days * 86400
    for key, value, path, age in (
        (ACCESS, session['access_token'], '/', int(session.get('expires_in', 3600))),
        (REFRESH, session['refresh_token'], AUTH_PATH, seconds),
    ):
        response.set_cookie(key, value, max_age=age, path=path,
            httponly=True, secure=settings.secure_cookies, samesite='lax')


def clear_session(response: Response, settings):
    for name, path in ((ACCESS, '/'), (REFRESH, AUTH_PATH)):
        response.delete_cookie(name, path=path, secure=settings.secure_cookies,
            httponly=True, samesite='lax')


def issue_csrf(response: Response, settings, existing=None):
    value = existing if existing and re.fullmatch(r'[A-Za-z0-9_-]{40,80}', existing) else secrets.token_urlsafe(32)
    response.set_cookie(CSRF, value, max_age=settings.session_days * 86400,
        path='/', secure=settings.secure_cookies, httponly=False, samesite='lax')
    return value


@dataclass
class CurrentUser:
    id: str
    email: str
    token: str
    profile: dict


async def current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(ACCESS)
    if not token:
        raise ApiError(401, 'AUTH_REQUIRED', '로그인이 필요합니다.')
    gateway = request.app.state.gateway
    user = await gateway.send('GET', '/auth/v1/user', token=token)
    rows = await gateway.table('users', token=token,
        params={'id': f'eq.{user["id"]}', 'select': '*'})
    if not rows:
        raise ApiError(401, 'AUTH_REQUIRED', '회원정보가 없습니다. 다시 로그인해 주세요.')
    return CurrentUser(user['id'], user.get('email', ''), token, rows[0])


class AuthLimiter:
    """Single-process coarse limiter; Supabase auth rate limits apply as well."""
    def __init__(self):
        self.attempts = defaultdict(deque)

    def check(self, request: Request, identity=''):
        now = monotonic()
        # Bound memory and do not trust client-supplied forwarded IP headers.
        for key in list(self.attempts):
            if not self.attempts[key] or now - self.attempts[key][-1] > 60:
                del self.attempts[key]
        host = request.client.host if request.client else 'unknown'
        key = (host, hashlib.sha256(identity.encode()).hexdigest()[:24])
        queue = self.attempts[key]
        while queue and now - queue[0] > 60:
            queue.popleft()
        if len(queue) >= 10 or len(self.attempts) > 10000:
            raise ApiError(429, 'RATE_LIMITED', '잠시 후 다시 로그인해 주세요.')
        queue.append(now)
