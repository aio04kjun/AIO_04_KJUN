from uuid import UUID

from fastapi import APIRouter, Depends, Request

from ..auth import CurrentUser, current_user
from ..errors import ApiError
from ..services.orders import own_order
from ..schemas import Input

router = APIRouter(prefix='/orders', tags=['결제'])


@router.post('/{order_id}/pay')
async def pay(order_id: UUID, body: Input, request: Request, user: CurrentUser = Depends(current_user)):
    if not request.app.state.settings.enable_mock_payments:
        raise ApiError(503, 'MOCK_PAYMENTS_DISABLED', '모의 결제가 활성화되어 있지 않습니다.')
    gateway = request.app.state.gateway
    await own_order(gateway, user, order_id)
    result = await gateway.rpc('pay_mock_order', admin=True,
        body={'p_order_id': str(order_id), 'p_user_id': user.id, 'p_should_succeed': True})
    return {'data': result}
