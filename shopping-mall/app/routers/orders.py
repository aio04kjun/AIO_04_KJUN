from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from ..auth import CurrentUser, current_user
from ..schemas import Input, OrderCreate
from ..services.orders import create_order, order_detail

router = APIRouter(prefix='/orders', tags=['주문'])


@router.post('')
async def create(body: OrderCreate, request: Request, user: CurrentUser = Depends(current_user)):
    # HTTP 200 also covers an idempotent retry returning an existing order.
    return {'data': await create_order(request.app.state.gateway, user, body)}


@router.get('')
async def orders(request: Request, status: Literal['pending', 'paid', 'cancelled'] | None = None,
                 page: int = Query(1, ge=1, le=100000), page_size: int = Query(10, ge=1, le=100),
                 user: CurrentUser = Depends(current_user)):
    params = {'user_id': f'eq.{user.id}', 'order': 'created_at.desc,id.desc',
        'offset': (page - 1) * page_size, 'limit': page_size + 1}
    if status:
        params['status'] = f'eq.{status}'
    rows = await request.app.state.gateway.table('orders', token=user.token, params=params)
    return {'data': rows[:page_size], 'pagination': {
        'page': page, 'page_size': page_size, 'has_more': len(rows) > page_size}}


@router.get('/{order_id}')
async def detail(order_id: UUID, request: Request, user: CurrentUser = Depends(current_user)):
    return {'data': await order_detail(request.app.state.gateway, user, order_id)}


@router.post('/{order_id}/cancel')
async def cancel(order_id: UUID, body: Input, request: Request, user: CurrentUser = Depends(current_user)):
    return {'data': await request.app.state.gateway.rpc('cancel_order', token=user.token,
        body={'p_order_id': str(order_id)})}
