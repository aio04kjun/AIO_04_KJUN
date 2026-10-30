"""Read-only Supabase API checks. Never prints API keys, tokens or user records."""
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

import httpx
from dotenv import dotenv_values
from app.config import Settings
from app.errors import ApiError
from app.supabase_client import SupabaseGateway


async def check():
    values = dotenv_values(PROJECT / '.env')
    required = ('SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'SUPABASE_SECRET_KEY')
    missing = [key for key in required if not values.get(key)]
    if missing:
        print('Missing: ' + ', '.join(missing))
        return 1
    parsed = urlsplit(values['SUPABASE_URL'])
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.supabase.co') or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        print('Invalid Supabase project URL. Expected an HTTPS project.supabase.co origin.')
        return 1
    public = values['SUPABASE_PUBLISHABLE_KEY']
    secret = values['SUPABASE_SECRET_KEY']
    if not public.startswith(('sb_publishable_', 'eyJ')) or not secret.startswith(('sb_secret_', 'eyJ')) or public == secret:
        print('API key format/type check failed. Check publishable/anon and secret/service_role fields.')
        return 1
    settings = Settings(values['SUPABASE_URL'].rstrip('/'), public, secret)
    async with httpx.AsyncClient(base_url=settings.supabase_url, timeout=15) as client:
        gateway = SupabaseGateway(settings, client)
        products = await gateway.table('products', params={'select': 'id,name,price,stock', 'is_active': 'eq.true', 'limit': 100})
        print(f'PASS: public Data API; {len(products)} active products returned (limit 100).')
        auth_settings = await gateway.send('GET', '/auth/v1/settings')
        print('PASS: Supabase Auth API reachable; email provider enabled: ' + str(auth_settings.get('external', {}).get('email')))
        for table in ('users', 'products', 'cart_items', 'orders', 'order_items', 'payments'):
            await gateway.send('GET', '/rest/v1/' + table, admin=True, params={'select': 'id', 'limit': 0})
        print('PASS: server key can access all six shop tables; no user records fetched.')
        print('Supabase API connection verified. No accounts or purchase records created.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(check()))
    except ApiError as exc:
        print(f'FAILED: HTTP {exc.status}; code={exc.code}. API keys and upstream response omitted.')
        raise SystemExit(1) from None
    except Exception as exc:
        print('FAILED: ' + type(exc).__name__ + '. Sensitive values omitted.')
        raise SystemExit(1) from None
