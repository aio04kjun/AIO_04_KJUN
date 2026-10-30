from fastapi import APIRouter, Depends, Request, Response

from ..auth import CurrentUser, clear_session, current_user
from ..errors import ApiError, not_found
from ..schemas import ProfileUpdate, Withdraw

router = APIRouter(prefix='/users', tags=['회원'])


@router.get('/me')
async def me(user: CurrentUser = Depends(current_user)):
    return {'data': {**user.profile, 'email': user.email}}


@router.patch('/me')
async def update_me(body: ProfileUpdate, request: Request,
                    user: CurrentUser = Depends(current_user)):
    rows = await request.app.state.gateway.table('users', token=user.token,
        method='PATCH', params={'id': f'eq.{user.id}'},
        body=body.model_dump(exclude_unset=True), prefer='return=representation')
    if not rows:
        raise not_found('회원')
    return {'data': {**rows[0], 'email': user.email}}


@router.delete('/me')
async def withdraw(body: Withdraw, request: Request, response: Response,
                   user: CurrentUser = Depends(current_user)):
    request.app.state.auth_limiter.check(request, user.id)
    gateway = request.app.state.gateway
    try:
        session = await gateway.send('POST', '/auth/v1/token',
            params={'grant_type': 'password'}, body={'email': user.email, 'password': body.password})
    except ApiError as exc:
        if exc.status in (400, 401):
            raise ApiError(401, 'INVALID_PASSWORD', '비밀번호를 확인해 주세요.') from exc
        raise
    if session.get('user', {}).get('id') != user.id:
        raise ApiError(403, 'REAUTH_FAILED', '본인 확인에 실패했습니다.')
    # Reauthentication created a temporary session; revoke it before account deletion.
    await gateway.send('POST', '/auth/v1/logout', token=session['access_token'], params={'scope': 'local'})
    await gateway.send('DELETE', f'/auth/v1/admin/users/{user.id}', admin=True)
    clear_session(response, request.app.state.settings)
    return {'data': {'message': '회원 탈퇴를 완료했습니다.'}}
