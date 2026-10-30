"""Local demo integration and HTML routing tests. No external services."""
import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings

P1 = '10000000-0000-4000-8000-000000000003'


class FrontendTests(unittest.TestCase):
    def setUp(self):
        settings = Settings('https://demo.invalid', 'demo-public', 'demo-secret',
            app_origin='http://testserver', enable_mock_payments=True, demo_mode=True)
        self.client = TestClient(create_app(settings))
        self.client.__enter__()
        token = self.client.get('/api/v1/auth/csrf').json()['data']['csrf_token']
        self.client.headers['X-CSRF-Token'] = token

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def login(self):
        result = self.client.post('/api/v1/auth/login', json={
            'email': 'demo@orbit.local', 'password': 'Orbit1234!', 'next': '/cart'})
        self.assertEqual(result.status_code, 200)
        return result

    def create_order(self, quantity=2):
        body = dict(order_id=str(uuid4()), items=[dict(product_id=P1, quantity=quantity)],
            recipient_name='체험회원', recipient_phone='010-0000-0000',
            shipping_address='01234 테스트 주소', expected_total=12000 * quantity)
        response = self.client.post('/api/v1/orders', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return body, response.json()['data']

    def test_public_pages_and_csp(self):
        for path in ('/', '/login', '/signup', '/products/' + P1):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/html', response.headers['content-type'])
            self.assertIn('lang="ko"', response.text)
            self.assertIn("script-src 'self'", response.headers['content-security-policy'])

    def test_guest_html_redirect_preserves_checkout_query(self):
        response = self.client.get(f'/checkout?product_id={P1}&quantity=2', follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn('/login?next=', response.headers['location'])
        self.assertIn('quantity%3D2', response.headers['location'])

    def test_all_protected_html_routes_reject_guests(self):
        for path in ('/cart', '/checkout', '/mypage', '/mypage/edit', '/mypage/orders', '/mypage/orders/' + str(uuid4())):
            self.assertEqual(self.client.get(path, follow_redirects=False).status_code, 303)

    def test_authenticated_page_access(self):
        self.login()
        self.assertEqual(self.client.get('/cart').status_code, 200)
        self.assertEqual(self.client.get('/mypage/edit').status_code, 200)

    def test_assets_are_available_and_do_not_expose_backend(self):
        for path in ('/assets/css/style.css', '/assets/js/app.js', '/assets/js/api.js', '/assets/images/hero.svg'):
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get('/assets/../app/config.py').status_code, 404)
        self.assertEqual(self.client.get('/.env').status_code, 404)

    def test_config_only_exposes_public_flags(self):
        response = self.client.get('/api/v1/config')
        self.assertEqual(response.json()['data'], {'demo_mode': True, 'mock_payments_enabled': True})
        self.assertNotIn('demo-secret', response.text)

    def test_demo_purchase_and_duplicate_payment(self):
        self.login()
        for _ in range(2):
            self.assertEqual(self.client.post('/api/v1/cart/items', json={'product_id': P1, 'quantity': 1}).status_code, 201)
        cart = self.client.get('/api/v1/cart').json()['data']
        self.assertEqual(len(cart['items']), 1)
        self.assertEqual(cart['items'][0]['quantity'], 2)
        body, order = self.create_order()
        self.assertEqual(self.client.post('/api/v1/orders', json=body).json()['data']['id'], order['id'])
        for _ in range(2):
            result = self.client.post('/api/v1/orders/' + order['id'] + '/pay', json={})
            self.assertEqual(result.json()['data']['payment']['status'], 'succeeded')
        self.assertEqual(self.client.get('/api/v1/products/' + P1).json()['data']['stock'], 13)
        history = self.client.get('/api/v1/orders?status=paid').json()['data']
        self.assertEqual(len(history), 1)
        detail = self.client.get('/api/v1/orders/' + order['id']).json()['data']
        self.assertEqual(detail['items'][0]['unit_price'], 12000)
        self.assertEqual(detail['payment']['status'], 'succeeded')
        self.assertEqual(self.client.get('/api/v1/cart').json()['data']['items'][0]['quantity'], 2)

    def test_demo_cancel_is_not_payable(self):
        self.login()
        _, order = self.create_order()
        self.assertEqual(self.client.post('/api/v1/orders/' + order['id'] + '/cancel', json={}).json()['data']['status'], 'cancelled')
        self.assertEqual(self.client.post('/api/v1/orders/' + order['id'] + '/pay', json={}).status_code, 409)

    def test_demo_profile_update_and_logout(self):
        self.login()
        response = self.client.patch('/api/v1/users/me', json={'name': '새 이름', 'phone': '010-1111-2222'})
        self.assertEqual(response.json()['data']['name'], '새 이름')
        self.assertEqual(self.client.post('/api/v1/auth/logout', json={}).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)

    def test_demo_signup_and_withdraw(self):
        signup = self.client.post('/api/v1/auth/signup', json={'email': 'new@example.com', 'password': 'Password123!', 'name': '신규회원'})
        self.assertTrue(signup.json()['data']['signed_in'])
        self.assertEqual(self.client.get('/api/v1/users/me').json()['data']['name'], '신규회원')
        self.assertEqual(self.client.request('DELETE', '/api/v1/users/me', json={'password': 'Password123!'}).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/users/me').status_code, 401)

    def test_demo_price_conflict_does_not_create_order(self):
        self.login()
        response = self.client.post('/api/v1/orders', json=dict(order_id=str(uuid4()),
            items=[dict(product_id=P1, quantity=1)], recipient_name='테스트',
            recipient_phone='010-0000-0000', shipping_address='테스트', expected_total=1))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'PRICE_CHANGED')
        self.assertEqual(self.client.get('/api/v1/orders').json()['data'], [])

    def test_demo_order_ownership(self):
        self.login()
        _, order = self.create_order()
        self.client.post('/api/v1/auth/logout', json={})
        self.client.post('/api/v1/auth/signup', json={'email': 'other@example.com', 'password': 'Password123!', 'name': '다른회원'})
        self.assertEqual(self.client.get('/api/v1/orders/' + order['id']).status_code, 404)
        self.assertEqual(self.client.post('/api/v1/orders/' + order['id'] + '/pay', json={}).status_code, 404)


if __name__ == '__main__':
    unittest.main()
