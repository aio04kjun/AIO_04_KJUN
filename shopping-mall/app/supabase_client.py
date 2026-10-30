"""Stateless Supabase Auth/PostgREST adapter. Never share user Authorization headers."""
import httpx

from .config import Settings
from .errors import ApiError

BUSINESS_ERRORS = {
    'PRICE_CHANGED': (409, '상품 가격이 변경되었습니다. 최신 금액을 확인해 주세요.'),
    'INSUFFICIENT_STOCK': (409, '상품 재고가 부족합니다.'),
    'PRODUCT_INACTIVE': (409, '판매 중지된 상품입니다.'),
    'PRODUCT_NOT_FOUND': (404, '상품을 찾을 수 없습니다.'),
    'USER_NOT_FOUND': (401, '다시 로그인해 주세요.'),
    'ORDER_NOT_FOUND': (404, '주문을 찾을 수 없습니다.'),
    'ORDER_FORBIDDEN': (403, '본인 주문만 처리할 수 있습니다.'),
    'ORDER_ID_CONFLICT': (409, '다른 주문 ID를 사용해 주세요.'),
    'IDEMPOTENCY_CONFLICT': (409, '같은 주문 ID로 다른 내용을 요청할 수 없습니다.'),
    'ORDER_NOT_PAYABLE': (409, '결제할 수 없는 주문 상태입니다.'),
    'PAID_ORDER_CANNOT_CANCEL': (409, '결제된 주문은 취소할 수 없습니다.'),
    'AUTH_REQUIRED': (401, '로그인이 필요합니다.'),
}


class SupabaseGateway:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client

    async def send(self, method, path, *, token=None, admin=False, params=None,
                   body=None, prefer=None):
        key = self.settings.secret_key if admin else self.settings.publishable_key
        headers = {'apikey': key, 'Accept': 'application/json'}
        # New sb_* keys belong in apikey only; legacy JWT keys also need Bearer.
        if token:
            headers['Authorization'] = f'Bearer {token}'
        elif key.startswith('eyJ'):
            headers['Authorization'] = f'Bearer {key}'
        if prefer:
            headers['Prefer'] = prefer
        try:
            response = await self.client.request(method, path, headers=headers,
                params=params, json=body)
        except httpx.RequestError as exc:
            raise ApiError(503, 'UPSTREAM_UNAVAILABLE', '데이터 서버에 연결할 수 없습니다.') from exc
        if response.is_error:
            self.raise_error(response, path)
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError(502, 'UPSTREAM_INVALID_RESPONSE', '데이터 서버 응답을 확인할 수 없습니다.') from exc

    @staticmethod
    def raise_error(response, path):
        try:
            info = response.json()
        except ValueError:
            info = {}
        code = str(info.get('message', '')) if isinstance(info, dict) else ''
        if code in BUSINESS_ERRORS:
            status, message = BUSINESS_ERRORS[code]
            raise ApiError(status, code, message)
        dbcode = info.get('code', '') if isinstance(info, dict) else ''
        if response.status_code == 429:
            raise ApiError(429, 'RATE_LIMITED', '요청이 많습니다. 잠시 후 다시 시도해 주세요.')
        if path == '/auth/v1/user' and response.status_code in (400, 401, 403, 404):
            # Stale demo tokens, expired JWTs and deleted auth users require a new login.
            raise ApiError(401, 'AUTH_REQUIRED', '인증이 만료되었습니다. 다시 로그인해 주세요.')
        if response.status_code == 401 or dbcode in ('PGRST301', 'PGRST303'):
            raise ApiError(401, 'AUTH_REQUIRED', '인증이 만료되었거나 로그인 정보가 올바르지 않습니다.')
        if path.startswith('/auth/v1/') and response.status_code in (400, 403, 422):
            raise ApiError(400, 'AUTH_FAILED', '인증 요청을 처리할 수 없습니다. 입력값과 이메일 인증 상태를 확인해 주세요.')
        if response.status_code == 403 or dbcode == '42501':
            raise ApiError(403, 'FORBIDDEN', '이 작업을 수행할 권한이 없습니다.')
        if dbcode == '23505':
            raise ApiError(409, 'ALREADY_EXISTS', '이미 존재하는 데이터입니다.')
        if dbcode in ('23503', '23514', '22003', '22P02', '22001'):
            raise ApiError(409, 'INVALID_DATA', '입력값 또는 현재 데이터 상태를 확인해 주세요.')
        # Never forward SQL details, auth tokens, or raw upstream errors to clients.
        raise ApiError(502, 'UPSTREAM_ERROR', '데이터 요청을 처리할 수 없습니다.')

    async def table(self, name, *, token=None, params=None, method='GET', body=None,
                    prefer=None):
        return await self.send(method, f'/rest/v1/{name}', token=token,
            params=params, body=body, prefer=prefer)

    async def rpc(self, name, body, *, token=None, admin=False):
        return await self.send('POST', f'/rest/v1/rpc/{name}', token=token,
            admin=admin, body=body)
