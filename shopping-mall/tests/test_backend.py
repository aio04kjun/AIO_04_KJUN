"""HTTP contract/security tests with a mocked Supabase HTTP boundary, not a live DB."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from fastapi.testclient import TestClient

from app.auth import ACCESS, REFRESH, safe_next
from app.config import Settings
from app.main import create_app

U1 = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
U2 = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
P1 = '10000000-0000-4000-8000-000000000003'
O1 = '20000000-0000-4000-8000-000000000001'
C1 = '30000000-0000-4000-8000-000000000001'


class FakeSupabase:
    def __init__(self):
        self.calls = []
        self.fail_connection = False
        self.rpc_error = None
        self.confirm_email = True
        self.fail_pay = False
        self.fail_refresh = False
        self.fail_reauth = False
        self.invalid_user_status = 401
        self.product = dict(id=P1, name='머그컵', description='', price=12000,
            stock=10, image_url=None, is_active=True)
        self.order = dict(id=O1, user_id=U1, status='pending', total_amount=24000,
            recipient_name='김하늘', recipient_phone='010-0000-0000',
            shipping_address='서울', created_at='2026-10-29T00:00:00Z')
        self.item = dict(id=C1, user_id=U1, product_id=P1, quantity=2)

    def session(self, uid=U1):
        return {'access_token': 'access-a' if uid == U1 else 'access-b',
            'refresh_token': 'refresh-a', 'expires_in': 3600,
            'user': {'id': uid, 'email': 'user@example.com'}}

    def __call__(self, request):
        body = json.loads(request.content) if request.content else None
        self.calls.append((request, body))
        if self.fail_connection:
            raise httpx.ConnectError('test network failure', request=request)
        path = request.url.path
        token = request.headers.get('authorization', '').removeprefix('Bearer ')
        uid = {'access-a': U1, 'access-b': U2}.get(token)
        if path == '/auth/v1/signup':
            return httpx.Response(200, json={'id': U1} if self.confirm_email else self.session())
        if path == '/auth/v1/token':
            if request.url.params.get('grant_type') == 'refresh_token' and self.fail_refresh:
                return httpx.Response(400, json={'message': 'invalid refresh token'})
            if body.get('password') == 'wrong-password' or self.fail_reauth:
                return httpx.Response(400, json={'message': 'Invalid login credentials'})
            return httpx.Response(200, json=self.session())
        if path == '/auth/v1/user':
            if not uid:
                return httpx.Response(self.invalid_user_status, json={'message': 'Invalid JWT'})
            return httpx.Response(200, json={'id': uid, 'email': 'user@example.com'})
        if path == '/auth/v1/logout':
            return httpx.Response(204) if uid else httpx.Response(401, json={'message': 'Invalid JWT'})
        if path.startswith('/auth/v1/admin/users/'):
            return httpx.Response(200, json={})
        if path == '/rest/v1/users':
            return httpx.Response(200, json=[{'id': uid, 'name': (body or {}).get('name', '김하늘'),
                'phone': (body or {}).get('phone'), 'created_at': '2026-10-29T00:00:00Z'}])
        if path == '/rest/v1/products':
            found = request.url.params.get('id', 'eq.' + P1) == 'eq.' + P1
            return httpx.Response(200, json=[self.product] if found else [])
        if path == '/rest/v1/cart_items':
            own = uid == U1 and request.url.params.get('id', 'eq.' + C1) in ('eq.' + C1, 'in.(' + C1 + ')')
            data = {**self.item, **(body or {})}
            if 'product:' in request.url.params.get('select', ''):
                data['product'] = self.product
            return httpx.Response(200, json=[data] if own else [])
        if path == '/rest/v1/orders':
            own = uid == U1 and request.url.params.get('id', 'eq.' + O1) == 'eq.' + O1
            return httpx.Response(200, json=[self.order] if own else [])
        if path == '/rest/v1/order_items':
            return httpx.Response(200, json=[dict(order_id=O1, product_id=P1,
                product_name='머그컵', unit_price=12000, quantity=2)])
        if path == '/rest/v1/payments':
            return httpx.Response(200, json=[])
        if path.startswith('/rest/v1/rpc/'):
            if self.rpc_error:
                return httpx.Response(400, json={'code': 'P0001', 'message': self.rpc_error})
            if path.endswith('/create_order'):
                return httpx.Response(200, json=self.order)
            if path.endswith('/add_cart_item'):
                return httpx.Response(200, json=self.item)
            if path.endswith('/cancel_order'):
                return httpx.Response(200, json={**self.order, 'status': 'cancelled'})
            if path.endswith('/pay_mock_order'):
                data = {'order': {**self.order, 'status': 'pending' if self.fail_pay else 'paid'},
                    'payment': {'id': 'M1', 'order_id': O1, 'amount': 24000,
                        'status': 'failed' if self.fail_pay else 'succeeded'}}
                if self.fail_pay:
                    data['failure_code'] = 'INSUFFICIENT_STOCK'
                return httpx.Response(200, json=data)
        raise AssertionError(f'Unexpected Supabase request: {request.method} {path}')


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.upstream = FakeSupabase()
        self.settings = Settings('https://supabase.test', 'sb_publishable_TEST',
            'sb_secret_SERVER_ONLY', 'http://testserver', enable_mock_payments=True)
        self.client = TestClient(create_app(self.settings, httpx.MockTransport(self.upstream)))
        self.client.__enter__()
        self.csrf = self.client.get('/api/v1/auth/csrf').json()['data']['csrf_token']
        self.client.headers['X-CSRF-Token'] = self.csrf

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def authenticate(self, token='access-a'):
        self.client.cookies.set(ACCESS, token)

    def order_body(self):
        return dict(order_id=O1, items=[{'product_id': P1, 'quantity': 2}],
            recipient_name='김하늘', recipient_phone='010-0000-0000',
            shipping_address='서울', expected_total=24000)

    def test_health_and_openapi(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        paths = self.client.get('/openapi.json').json()['paths']
        self.assertIn('/api/v1/orders/{order_id}/pay', paths)
        self.assertIn('/api/v1/users/me', paths)

    def test_public_products_and_pagination_validation(self):
        result = self.client.get('/api/v1/products')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['data'][0]['price'], 12000)
        self.assertEqual(self.client.get('/api/v1/products?page_size=101').status_code, 422)
        self.assertEqual(result.headers['cache-control'], 'no-store')

    def test_missing_product(self):
        self.assertEqual(self.client.get('/api/v1/products/' + O1).status_code, 404)

    def test_guest_protected_endpoints_return_json_401(self):
        for path in ('/users/me', '/cart', '/orders', '/orders/' + O1):
            response = self.client.get('/api/v1' + path)
            self.assertEqual(response.status_code, 401, path)
            self.assertEqual(response.json()['error']['code'], 'AUTH_REQUIRED')

    def test_stale_demo_or_invalid_user_token_requires_login(self):
        self.authenticate('stale-demo-token')
        for provider_status in (400, 403, 404):
            self.upstream.invalid_user_status = provider_status
            response = self.client.get('/api/v1/users/me')
            self.assertEqual(response.status_code, 401)
            response = self.client.get('/cart', follow_redirects=False)
            self.assertEqual(response.status_code, 303)
            self.assertIn('/login?next=', response.headers['location'])

    def test_csrf_and_origin_block_writes(self):
        self.authenticate()
        self.assertEqual(self.client.post('/api/v1/orders', json=self.order_body(),
            headers={'X-CSRF-Token': ''}).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/orders', json=self.order_body(),
            headers={'Origin': 'https://evil.test'}).status_code, 403)
        self.assertEqual(self.upstream.calls, [])

    def test_non_json_write_is_rejected(self):
        result = self.client.post('/api/v1/auth/login', content='email=x',
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        self.assertEqual(result.status_code, 415)

    def test_login_sets_private_cookies_and_safe_next(self):
        result = self.client.post('/api/v1/auth/login', json={
            'email': 'USER@example.com', 'password': 'correct-password',
            'next': '/checkout?product_id=' + P1 + '&quantity=2'})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()['data']['next'].startswith('/checkout?'))
        cookies = result.headers.get_list('set-cookie')
        self.assertTrue(all('HttpOnly' in value for value in cookies))
        self.assertTrue(any('Path=/api/v1/auth' in value for value in cookies))
        self.assertNotIn('access-a', result.text)

    def test_login_rejects_external_next(self):
        result = self.client.post('/api/v1/auth/login', json={
            'email': 'user@example.com', 'password': 'correct-password', 'next': '//evil.test'})
        self.assertEqual(result.json()['data']['next'], '/')

    def test_invalid_login_does_not_leak_upstream(self):
        result = self.client.post('/api/v1/auth/login', json={
            'email': 'user@example.com', 'password': 'wrong-password'})
        self.assertEqual(result.status_code, 401)
        self.assertNotIn('Invalid login credentials', result.text)

    def test_signup_confirmation_does_not_fake_a_session(self):
        response = self.client.post('/api/v1/auth/signup', json={
            'email': 'new@example.com', 'password': 'valid-password', 'name': '신규회원'})
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['data']['signed_in'])
        self.assertNotIn(ACCESS, self.client.cookies)

    def test_signup_without_confirmation_sets_session(self):
        self.upstream.confirm_email = False
        response = self.client.post('/api/v1/auth/signup', json={
            'email': 'new@example.com', 'password': 'valid-password', 'name': '신규회원'})
        self.assertTrue(response.json()['data']['signed_in'])
        self.assertEqual(self.client.cookies.get(ACCESS), 'access-a')

    def test_refresh_rotates_cookies(self):
        self.client.cookies.set(REFRESH, 'refresh-a')
        result = self.client.post('/api/v1/auth/refresh', json={})
        self.assertEqual(result.status_code, 200)
        self.assertNotIn('refresh-a', result.text)

    def test_invalid_refresh_deletes_cookies(self):
        self.client.cookies.set(REFRESH, 'refresh-a')
        self.upstream.fail_refresh = True
        result = self.client.post('/api/v1/auth/refresh', json={})
        self.assertEqual(result.status_code, 401)
        self.assertTrue(any('Max-Age=0' in value for value in result.headers.get_list('set-cookie')))

    def test_logout_expired_access_uses_refresh_and_revokes(self):
        self.authenticate('expired')
        self.client.cookies.set(REFRESH, 'refresh-a')
        result = self.client.post('/api/v1/auth/logout', json={})
        self.assertEqual(result.status_code, 200)
        logout_calls = [r for r, _ in self.upstream.calls if r.url.path.endswith('/logout')]
        self.assertEqual(logout_calls[-1].headers['authorization'], 'Bearer access-a')

    def test_profile_is_scoped_to_validated_user(self):
        self.authenticate()
        result = self.client.patch('/api/v1/users/me', json={'name': '새 이름', 'phone': None})
        self.assertEqual(result.json()['data']['name'], '새 이름')
        self.assertEqual(self.upstream.calls[-1][0].url.params['id'], 'eq.' + U1)

    def test_profile_primary_key_injection_rejected(self):
        self.authenticate()
        result = self.client.patch('/api/v1/users/me', json={'id': U2})
        self.assertEqual(result.status_code, 422)

    def test_withdraw_requires_password_and_uses_server_key(self):
        self.authenticate()
        response = self.client.request('DELETE', '/api/v1/users/me', json={'password': 'correct-password'})
        self.assertEqual(response.status_code, 200)
        request, _ = self.upstream.calls[-1]
        self.assertEqual(request.url.path, '/auth/v1/admin/users/' + U1)
        self.assertEqual(request.headers['apikey'], self.settings.secret_key)
        self.assertNotIn(self.settings.secret_key, response.text)

    def test_bad_password_never_deletes_account(self):
        self.authenticate()
        response = self.client.request('DELETE', '/api/v1/users/me', json={'password': 'wrong-password'})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(any('/admin/users/' in r.url.path for r, _ in self.upstream.calls))

    def test_cart_add_calls_atomic_rpc_with_user_jwt(self):
        self.authenticate()
        response = self.client.post('/api/v1/cart/items', json={'product_id': P1, 'quantity': 2})
        self.assertEqual(response.status_code, 201)
        request, body = self.upstream.calls[-1]
        self.assertTrue(request.url.path.endswith('/add_cart_item'))
        self.assertEqual(request.headers['authorization'], 'Bearer access-a')
        self.assertEqual(body['p_quantity'], 2)

    def test_invalid_quantity_bool_and_zero_rejected(self):
        self.authenticate()
        for value in (0, True, -1, 1.5):
            result = self.client.post('/api/v1/cart/items', json={'product_id': P1, 'quantity': value})
            self.assertEqual(result.status_code, 422)

    def test_cart_totals_and_quantity_change(self):
        self.authenticate()
        self.assertEqual(self.client.get('/api/v1/cart').json()['data']['total_amount'], 24000)
        response = self.client.patch('/api/v1/cart/items/' + C1, json={'quantity': 11})
        self.assertEqual(response.status_code, 409)

    def test_cart_update_delete_and_clear_are_user_scoped(self):
        self.authenticate()
        changed = self.client.patch('/api/v1/cart/items/' + C1, json={'quantity': 3})
        self.assertEqual(changed.json()['data']['quantity'], 3)
        deleted = self.client.request('DELETE', '/api/v1/cart/items/' + C1, json={})
        self.assertTrue(deleted.json()['data']['deleted'])
        cleared = self.client.request('DELETE', '/api/v1/cart', json={})
        self.assertTrue(cleared.json()['data']['deleted'])
        for request, _ in self.upstream.calls:
            if request.url.path == '/rest/v1/cart_items' and request.method in ('PATCH', 'DELETE'):
                self.assertEqual(request.url.params['user_id'], 'eq.' + U1)

    def test_secure_cookie_flags_for_https_settings(self):
        secure = Settings('https://supabase.test', 'p', 's', 'http://testserver', secure_cookies=True)
        with patch.object(self.client.app.state, 'settings', secure):
            result = self.client.post('/api/v1/auth/login', json={
                'email': 'user@example.com', 'password': 'correct-password'})
        self.assertTrue(all('Secure' in value and 'HttpOnly' in value
            for value in result.headers.get_list('set-cookie')))

    def test_internal_sql_errors_are_not_exposed(self):
        self.authenticate()
        self.upstream.rpc_error = 'PRIVATE_DATABASE_DETAILS'
        response = self.client.post('/api/v1/orders', json=self.order_body())
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('PRIVATE_DATABASE_DETAILS', response.text)

    def test_client_cannot_select_payment_identity_or_result(self):
        self.authenticate()
        response = self.client.post('/api/v1/orders/' + O1 + '/pay',
            json={'p_user_id': U2, 'p_should_succeed': True})
        self.assertEqual(response.status_code, 422)
        self.assertFalse(any(r.url.path.endswith('/pay_mock_order') for r, _ in self.upstream.calls))

    def test_direct_order_uses_database_price_validation(self):
        self.authenticate()
        response = self.client.post('/api/v1/orders', json=self.order_body())
        self.assertEqual(response.status_code, 200)
        request, payload = self.upstream.calls[-1]
        self.assertTrue(request.url.path.endswith('/create_order'))
        self.assertEqual(payload['p_expected_total'], 24000)
        self.assertNotIn('p_user_id', payload)

    def test_checkout_payload_is_independent_of_later_cart_changes(self):
        self.authenticate()
        body = self.order_body()
        self.upstream.item['quantity'] = 9
        response = self.client.post('/api/v1/orders', json=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.upstream.calls[-1][1]['p_items'][0]['quantity'], 2)

    def test_order_with_both_sources_rejected(self):
        self.authenticate()
        body = {**self.order_body(), 'cart_item_ids': [C1]}
        self.assertEqual(self.client.post('/api/v1/orders', json=body).status_code, 422)

    def test_price_changed_is_409(self):
        self.authenticate()
        self.upstream.rpc_error = 'PRICE_CHANGED'
        response = self.client.post('/api/v1/orders', json=self.order_body())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'PRICE_CHANGED')

    def test_order_detail_and_cancel(self):
        self.authenticate()
        detail = self.client.get('/api/v1/orders/' + O1).json()['data']
        self.assertEqual(detail['items'][0]['quantity'], 2)
        self.assertIsNone(detail['payment'])
        self.assertEqual(self.client.post('/api/v1/orders/' + O1 + '/cancel', json={}).json()['data']['status'], 'cancelled')

    def test_payment_uses_verified_id_and_admin_key_only_for_rpc(self):
        self.authenticate()
        response = self.client.post('/api/v1/orders/' + O1 + '/pay', json={})
        self.assertEqual(response.json()['data']['payment']['status'], 'succeeded')
        request, body = self.upstream.calls[-1]
        self.assertEqual(request.headers['apikey'], self.settings.secret_key)
        self.assertEqual(body['p_user_id'], U1)
        self.assertNotIn('authorization', request.headers)

    def test_other_user_cannot_trigger_admin_payment(self):
        self.authenticate('access-b')
        response = self.client.post('/api/v1/orders/' + O1 + '/pay', json={})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(any(r.url.path.endswith('/pay_mock_order') for r, _ in self.upstream.calls))

    def test_failed_payment_preserves_business_result(self):
        self.authenticate()
        self.upstream.fail_pay = True
        data = self.client.post('/api/v1/orders/' + O1 + '/pay', json={}).json()['data']
        self.assertEqual(data['payment']['status'], 'failed')
        self.assertEqual(data['failure_code'], 'INSUFFICIENT_STOCK')

    def test_mock_payments_can_be_disabled(self):
        self.authenticate()
        with patch.object(self.client.app.state, 'settings', Settings('https://supabase.test', 'p', 's')):
            self.assertEqual(self.client.post('/api/v1/orders/' + O1 + '/pay', json={}).status_code, 503)

    def test_user_authorization_does_not_leak_between_requests(self):
        self.authenticate()
        self.assertEqual(self.client.get('/api/v1/users/me').json()['data']['id'], U1)
        self.client.cookies.set(ACCESS, 'access-b')
        self.assertEqual(self.client.get('/api/v1/users/me').json()['data']['id'], U2)
        self.assertNotIn('authorization', self.client.app.state.gateway.client.headers)

    def test_provider_network_failure_is_json_503(self):
        self.upstream.fail_connection = True
        response = self.client.get('/api/v1/products')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('test network failure', response.text)

    def test_validation_errors_never_echo_password(self):
        secret = 'x' * 129
        response = self.client.post('/api/v1/auth/login', json={'email': 'bad', 'password': secret})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)

    def test_local_auth_rate_limit(self):
        payload = {'email': 'user@example.com', 'password': 'wrong-password'}
        for _ in range(10):
            self.assertEqual(self.client.post('/api/v1/auth/login', json=payload).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/login', json=payload).status_code, 429)


class NextTests(unittest.TestCase):
    def test_redirect_attack_cases(self):
        for value in ('https://evil.test', '//evil.test', '/%2fevil.test', '/\\evil.test',
                      '/%255cevil.test', '/login', '/api/v1/orders', '/cart\r\nX: y'):
            with self.subTest(value=value):
                self.assertEqual(safe_next(value), '/')

    def test_internal_routes_preserve_query(self):
        self.assertEqual(safe_next('/checkout?product_id=' + P1 + '&quantity=2'),
            '/checkout?product_id=' + P1 + '&quantity=2')
        self.assertEqual(safe_next('/mypage/orders/' + O1), '/mypage/orders/' + O1)


if __name__ == '__main__':
    unittest.main()
