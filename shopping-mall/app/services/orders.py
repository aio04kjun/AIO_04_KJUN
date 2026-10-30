import asyncio

from ..errors import not_found


async def own_order(gateway, user, order_id):
    rows = await gateway.table('orders', token=user.token, params={
        'id': f'eq.{order_id}', 'user_id': f'eq.{user.id}'})
    if not rows:
        raise not_found('주문')
    return rows[0]


async def order_detail(gateway, user, order_id):
    order = await own_order(gateway, user, order_id)
    items, payments = await asyncio.gather(
        gateway.table('order_items', token=user.token,
            params={'order_id': f'eq.{order_id}', 'order': 'id.asc'}),
        gateway.table('payments', token=user.token, params={'order_id': f'eq.{order_id}'}))
    return {**order, 'items': items, 'payment': payments[0] if payments else None}


async def create_order(gateway, user, body):
    # Send a stable item snapshot; later cart edits must not change a retried request.
    items = [item.model_dump(mode='json') for item in body.items]
    return await gateway.rpc('create_order', token=user.token, body={
        'p_order_id': str(body.order_id), 'p_items': items,
        'p_recipient_name': body.recipient_name, 'p_recipient_phone': body.recipient_phone,
        'p_shipping_address': body.shipping_address, 'p_expected_total': body.expected_total})
