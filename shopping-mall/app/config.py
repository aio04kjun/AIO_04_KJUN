import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    publishable_key: str
    secret_key: str
    app_origin: str = 'http://localhost:8000'
    secure_cookies: bool = False
    enable_mock_payments: bool = False
    session_days: int = 7
    demo_mode: bool = False

    @classmethod
    def from_env(cls):
        if os.getenv('SHOP_DEMO', 'false').lower() == 'true':
            origin = os.getenv('APP_ORIGIN', 'http://localhost:8000').rstrip('/')
            if urlsplit(origin).hostname not in ('localhost', '127.0.0.1'):
                raise RuntimeError('Demo mode is restricted to localhost')
            return cls('https://demo.invalid', 'demo-public', 'demo-secret',
                       app_origin=origin, enable_mock_payments=True, demo_mode=True)
        required = ['SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'SUPABASE_SECRET_KEY']
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError('Missing environment variables: ' + ', '.join(missing))
        origin = os.getenv('APP_ORIGIN', 'http://localhost:8000').rstrip('/')
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path:
            raise RuntimeError('APP_ORIGIN must be an http(s) origin without a path')
        secure = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
        if parsed.scheme == 'https' and not secure:
            raise RuntimeError('HTTPS deployment requires COOKIE_SECURE=true')
        return cls(os.environ['SUPABASE_URL'].rstrip('/'),
                   os.environ['SUPABASE_PUBLISHABLE_KEY'], os.environ['SUPABASE_SECRET_KEY'],
                   origin, secure, os.getenv('ENABLE_MOCK_PAYMENTS', 'false').lower() == 'true')
