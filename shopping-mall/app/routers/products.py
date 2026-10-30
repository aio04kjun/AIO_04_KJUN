from uuid import UUID

from fastapi import APIRouter, Query, Request

from ..errors import not_found

router = APIRouter(prefix='/products', tags=['상품'])


@router.get('')
async def products(request: Request, page: int = Query(1, ge=1, le=100000),
                   page_size: int = Query(12, ge=1, le=100)):
    rows = await request.app.state.gateway.table('products', params={
        'select': '*', 'is_active': 'eq.true', 'order': 'id.asc',
        'offset': (page - 1) * page_size, 'limit': page_size + 1})
    return {'data': rows[:page_size], 'pagination': {
        'page': page, 'page_size': page_size, 'has_more': len(rows) > page_size}}


@router.get('/{product_id}')
async def product(product_id: UUID, request: Request):
    rows = await request.app.state.gateway.table('products', params={
        'select': '*', 'id': f'eq.{product_id}', 'is_active': 'eq.true'})
    if not rows:
        raise not_found('상품')
    return {'data': rows[0]}
