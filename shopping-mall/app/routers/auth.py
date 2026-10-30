from fastapi import APIRouter, Request, Response

from ..auth import (ACCESS, REFRESH, CSRF, clear_session, issue_csrf, safe_next, set_session)
from ..errors import ApiError
from ..schemas import Input, Login, Signup

router = APIRouter(prefix='/auth', tags=['인증'])


@router.get('/csrf')
async def csrf(request: Request, response: Response):
    token = issue_csrf(response, request.app.state.settings, request.cookies.get(CSRF))
    return {'data': {'csrf_token': token}}


@router.post('/signup', status_code=201)
async def signup(body: Signup, request: Request, response: Response):
    request.app.state.auth_limiter.check(request, body.email)
    result = await request.app.state.gateway.send('POST', '/auth/v1/signup', body={
        'email': body.email, 'password': body.password, 'data': {'name': body.name}})
    signed_in = bool(result.get('access_token'))
    if signed_in:
        set_session(response, result, request.app.state.settings)
    # Do not expose duplicate-account detection or session tokens in JSON.
    return {'data': {'signed_in': signed_in,
        'message': '가입 요청을 처리했습니다. 이메일 인증이 설정된 경우 메일을 확인해 주세요.'}}


@router.post('/login')
async def login(body: Login, request: Request, response: Response):
    request.app.state.auth_limiter.check(request, body.email)
    try:
        result = await request.app.state.gateway.send('POST', '/auth/v1/token',
            params={'grant_type': 'password'}, body={'email': body.email, 'password': body.password})
    except ApiError as exc:
        if exc.status in (400, 401):
            raise ApiError(401, 'INVALID_CREDENTIALS', '이메일·비밀번호 또는 이메일 인증 상태를 확인해 주세요.') from exc
        raise
    set_session(response, result, request.app.state.settings)
    return {'data': {'next': safe_next(body.next), 'expires_in': result.get('expires_in', 3600)}}


@router.post('/refresh')
async def refresh(body: Input, request: Request, response: Response):
    token = request.cookies.get(REFRESH)
    request.app.state.auth_limiter.check(request, token or 'missing-refresh')
    if not token:
        raise ApiError(401, 'AUTH_REQUIRED', '다시 로그인해 주세요.')
    try:
        result = await request.app.state.gateway.send('POST', '/auth/v1/token',
            params={'grant_type': 'refresh_token'}, body={'refresh_token': token})
    except ApiError as exc:
        if exc.status in (400, 401):
            # Return the response directly so cookie deletion is retained on failure.
            from fastapi.responses import JSONResponse
            failed = JSONResponse({'error': {'code': 'AUTH_REQUIRED', 'message': '다시 로그인해 주세요.'}}, status_code=401)
            clear_session(failed, request.app.state.settings)
            return failed
        raise
    set_session(response, result, request.app.state.settings)
    return {'data': {'expires_in': result.get('expires_in', 3600)}}


@router.post('/logout')
async def logout(body: Input, request: Request, response: Response):
    gateway = request.app.state.gateway
    token = request.cookies.get(ACCESS)
    revoked = False
    if token:
        try:
            await gateway.send('POST', '/auth/v1/logout', token=token, params={'scope': 'local'})
            revoked = True
        except ApiError as exc:
            if exc.status not in (400, 401, 403):
                raise
    # An expired access token must not leave a valid refresh session behind.
    if not revoked and request.cookies.get(REFRESH):
        try:
            session = await gateway.send('POST', '/auth/v1/token',
                params={'grant_type': 'refresh_token'},
                body={'refresh_token': request.cookies[REFRESH]})
            token = session['access_token']
        except ApiError as exc:
            if exc.status not in (400, 401, 403):
                raise
    if not revoked and token:
        try:
            await gateway.send('POST', '/auth/v1/logout', token=token, params={'scope': 'local'})
        except ApiError as exc:
            if exc.status not in (400, 401, 403):
                raise
    clear_session(response, request.app.state.settings)
    return {'data': {'message': '로그아웃했습니다.'}}
