from contextlib import asynccontextmanager
import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .auth import AuthLimiter, csrf_error
from .config import Settings
from .errors import ApiError
from .routers import auth, cart, orders, payments, products, users
from .supabase_client import SupabaseGateway
from .web import install_web


def create_app(settings: Settings | None = None, transport=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings.from_env()
        app.state.auth_limiter = AuthLimiter()
        selected_transport = transport
        if app.state.settings.demo_mode and selected_transport is None:
            from .demo import DemoStore
            app.state.demo_store = DemoStore()
            selected_transport = httpx.MockTransport(app.state.demo_store.handle)
        async with httpx.AsyncClient(base_url=app.state.settings.supabase_url,
            timeout=httpx.Timeout(15, connect=5), transport=selected_transport,
            follow_redirects=False) as client:
            app.state.gateway = SupabaseGateway(app.state.settings, client)
            yield

    app = FastAPI(title='Shopping Mall API', version='1.0.0', lifespan=lifespan,
                  description='Supabase Auth + PostgreSQL / Vanilla HTML·CSS·JS / 모의 결제')

    @app.middleware('http')
    async def security(request: Request, call_next):
        if request.url.path.startswith('/api/'):
            error = csrf_error(request)
            if error:
                response = JSONResponse({'error': {'code': error.code, 'message': error.message}}, status_code=error.status)
            else:
                response = await call_next(request)
            response.headers['Cache-Control'] = 'no-store'
        else:
            response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return JSONResponse({'error': {'code': exc.code, 'message': exc.message}}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Pydantic's default error payload includes input values (including passwords).
        details = [{'field': '.'.join(map(str, error['loc'])), 'message': error['msg']}
                   for error in exc.errors()]
        return JSONResponse({'error': {'code': 'VALIDATION_ERROR', 'message': '입력값을 확인해 주세요.',
            'details': details}}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({'error': {'code': 'HTTP_ERROR', 'message': str(exc.detail)}},
            status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logging.getLogger(__name__).error('Unhandled server error', exc_info=exc)
        return JSONResponse({'error': {'code': 'INTERNAL_ERROR', 'message': '서버 오류가 발생했습니다.'}},
            status_code=500, headers={'Cache-Control': 'no-store'})

    @app.get('/health', tags=['운영'])
    async def health():
        return {'data': {'status': 'ok'}}

    @app.get('/api/v1/config', tags=['운영'])
    async def public_config(request: Request):
        settings = request.app.state.settings
        return {'data': {'demo_mode': settings.demo_mode,
                         'mock_payments_enabled': settings.enable_mock_payments}}

    for router in (auth.router, users.router, products.router, cart.router, orders.router, payments.router):
        app.include_router(router, prefix='/api/v1')
    original_openapi = app.openapi

    def documented_openapi():
        schema = original_openapi()
        for path, methods in schema['paths'].items():
            for method, operation in methods.items():
                if path.startswith('/api/') and method in ('post', 'patch', 'delete', 'put'):
                    parameters = operation.setdefault('parameters', [])
                    if not any(p.get('name') == 'X-CSRF-Token' for p in parameters):
                        parameters.append({'name': 'X-CSRF-Token', 'in': 'header', 'required': True,
                            'schema': {'type': 'string'},
                            'description': 'GET /api/v1/auth/csrf에서 발급한 토큰. 쿠키도 함께 전송합니다.'})
        return schema

    app.openapi = documented_openapi
    install_web(app)
    return app


app = create_app()
