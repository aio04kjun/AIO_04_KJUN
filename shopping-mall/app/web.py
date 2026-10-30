from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID

from fastapi import Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .auth import current_user, safe_next
from .errors import ApiError

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'


def install_web(app):
    async def page(request: Request):
        protected = request.url.path in ('/cart', '/checkout') or request.url.path.startswith('/mypage')
        if protected:
            try:
                await current_user(request)
            except ApiError as exc:
                if exc.status != 401:
                    raise
                target = request.url.path + ('?' + request.url.query if request.url.query else '')
                return RedirectResponse('/login?' + urlencode({'next': safe_next(target)}),
                    status_code=303, headers={'Cache-Control': 'no-store'})
        return FileResponse(FRONTEND / 'index.html', headers={
            'Cache-Control': 'no-store',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' https:; connect-src 'self'; object-src 'none'; "
                "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"})

    for path in ('/', '/login', '/signup', '/cart', '/checkout', '/mypage', '/mypage/edit', '/mypage/orders'):
        app.add_api_route(path, page, methods=['GET'], include_in_schema=False)

    @app.get('/products/{product_id}', include_in_schema=False)
    async def product_page(product_id: UUID, request: Request):
        return await page(request)

    @app.get('/mypage/orders/{order_id}', include_in_schema=False)
    async def order_page(order_id: UUID, request: Request):
        return await page(request)

    app.mount('/assets', StaticFiles(directory=FRONTEND / 'assets'), name='assets')
