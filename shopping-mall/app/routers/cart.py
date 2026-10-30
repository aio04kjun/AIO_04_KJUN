from uuid import UUID

from fastapi import APIRouter, Depends, Request

from ..auth import CurrentUser, current_user
from ..errors import ApiError, not_found
from ..schemas import CartAdd, CartUpdate, Input

router = APIRouter(prefix='/cart', tags=['장바구니'])


@router.get('')
async def cart(request: Request, user: CurrentUser = Depends(current_user)):
    rows = await request.app.state.gateway.table('cart_items', token=user.token, params={
        'select': '*,product:products(id,name,price,stock,image_url,is_active)',
        'user_id': f'eq.{user.id}', 'order': 'id.asc'})
    total = 0
    for row in rows:
        product = row.get('product')
        row['available'] = bool(product and product['is_active'] and product['stock'] >= row['quantity'])
        row['subtotal'] = product['price'] * row['quantity'] if product else 0
        total += row['subtotal']
    return {'data': {'items': rows, 'total_amount': total}}


@router.post('/items', status_code=201)
async def add(body: CartAdd, request: Request, user: CurrentUser = Depends(current_user)):
    result = await request.app.state.gateway.rpc('add_cart_item', token=user.token,
        body={'p_product_id': str(body.product_id), 'p_quantity': body.quantity})
    return {'data': result}


@router.patch('/items/{item_id}')
async def change(item_id: UUID, body: CartUpdate, request: Request,
                 user: CurrentUser = Depends(current_user)):
    gateway = request.app.state.gateway
    filters = {'id': f'eq.{item_id}', 'user_id': f'eq.{user.id}'}
    rows = await gateway.table('cart_items', token=user.token, params=filters)
    if not rows:
        raise not_found('장바구니 항목')
    products = await gateway.table('products', token=user.token, params={
        'id': f'eq.{rows[0]["product_id"]}', 'is_active': 'eq.true'})
    if not products:
        raise ApiError(409, 'PRODUCT_INACTIVE', '구매할 수 없는 상품입니다.')
    if products[0]['stock'] < body.quantity:
        raise ApiError(409, 'INSUFFICIENT_STOCK', '상품 재고가 부족합니다.')
    updated = await gateway.table('cart_items', token=user.token, params=filters,
        method='PATCH', body={'quantity': body.quantity}, prefer='return=representation')
    if not updated:
        raise not_found('장바구니 항목')
    return {'data': updated[0]}


@router.delete('/items/{item_id}')
async def remove(item_id: UUID, body: Input, request: Request, user: CurrentUser = Depends(current_user)):
    rows = await request.app.state.gateway.table('cart_items', token=user.token,
        method='DELETE', params={'id': f'eq.{item_id}', 'user_id': f'eq.{user.id}'},
        prefer='return=representation')
    if not rows:
        raise not_found('장바구니 항목')
    return {'data': {'deleted': True}}


@router.delete('')
async def clear(body: Input, request: Request, user: CurrentUser = Depends(current_user)):
    await request.app.state.gateway.table('cart_items', token=user.token,
        method='DELETE', params={'user_id': f'eq.{user.id}'})
    return {'data': {'deleted': True}}
