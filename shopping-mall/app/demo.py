"""Local-only, in-memory Supabase boundary simulator. Never used in live mode."""
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from uuid import uuid4

import httpx


def now():
    return datetime.now(timezone.utc).isoformat()


class DemoStore:
    def __init__(self):
        self.users = {}
        self.access = {}
        self.refresh = {}
        self.cart = {}
        self.orders = {}
        self.items = {}
        self.payments = {}
        self.products = {}
        seeds = [('베이직 반팔 티셔츠', '편안하게 흐르는 실루엣, 매일 손이 가는 면 티셔츠입니다.', 19000, 30),
                 ('캔버스 에코백', '가볍게 나서는 날, 필요한 물건을 넉넉하게 담아 보세요.', 15000, 20),
                 ('데일리 머그컵', '따뜻한 한 모금과 함께, 잠깐의 여유를 위한 머그컵입니다.', 12000, 15),
                 ('스테인리스 텀블러', '나의 페이스대로. 일상과 여행에 함께하는 텀블러입니다.', 25000, 5),
                 ('메모 노트', '문득 떠오른 생각과 작은 계획을 담아 두는 노트입니다.', 5000, 0)]
        for index, (name, description, price, stock) in enumerate(seeds, 1):
            product_id = f'10000000-0000-4000-8000-{index:012d}'
            self.products[product_id] = dict(id=product_id, name=name, description=description,
                price=price, stock=stock, image_url=None, is_active=True)
        self.register('demo@orbit.local', 'Orbit1234!', '우주 여행자')

    def register(self, email, password, name):
        uid, salt = str(uuid4()), secrets.token_bytes(16)
        self.users[uid] = dict(id=uid, email=email, name=name, phone=None, created_at=now(),
            salt=salt, password_hash=hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1))
        return uid

    def session(self, uid):
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.access[access] = dict(uid=uid, expires=time.time() + 3600, refresh=refresh)
        self.refresh[refresh] = dict(uid=uid, access=access)
        return dict(access_token=access, refresh_token=refresh, expires_in=3600,
            user={'id': uid, 'email': self.users[uid]['email']})

    def profile(self, uid):
        return {k: v for k, v in self.users[uid].items() if k not in ('salt', 'password_hash', 'email')}

    @staticmethod
    def error(message, status=400, code='P0001'):
        return httpx.Response(status, json={'code': code, 'message': message})

    def handle(self, request):
        body = json.loads(request.content) if request.content else {}
        body = body or {}
        path, method, params = request.url.path, request.method, request.url.params
        token = request.headers.get('Authorization', '').removeprefix('Bearer ')
        session = self.access.get(token, {})
        uid = session.get('uid') if session.get('expires', 0) > time.time() else None
        admin = request.headers.get('apikey') == 'demo-secret'
        if path == '/auth/v1/signup':
            email = body['email']
            if any(u['email'] == email for u in self.users.values()):
                return self.error('Account already exists')
            uid = self.register(email, body['password'], body.get('data', {}).get('name', '회원'))
            return httpx.Response(200, json=self.session(uid))
        if path == '/auth/v1/token':
            if params.get('grant_type') == 'refresh_token':
                record = self.refresh.pop(body.get('refresh_token'), None)
                if not record or record['uid'] not in self.users:
                    return self.error('Invalid refresh token', 401)
                self.access.pop(record['access'], None)
                return httpx.Response(200, json=self.session(record['uid']))
            user = next((u for u in self.users.values() if u['email'] == body.get('email')), None)
            if not user or not hmac.compare_digest(user['password_hash'], hashlib.scrypt(
                body.get('password', '').encode(), salt=user['salt'], n=16384, r=8, p=1)):
                return self.error('Invalid credentials', 401)
            return httpx.Response(200, json=self.session(user['id']))
        if path == '/auth/v1/user':
            if not uid or uid not in self.users:
                return self.error('Invalid JWT', 401)
            return httpx.Response(200, json={'id': uid, 'email': self.users[uid]['email']})
        if path == '/auth/v1/logout':
            if not uid:
                return self.error('Invalid JWT', 401)
            record = self.access.pop(token)
            self.refresh.pop(record['refresh'], None)
            return httpx.Response(204)
        if path.startswith('/auth/v1/admin/users/') and method == 'DELETE' and admin:
            target = path.rsplit('/', 1)[-1]
            self.users.pop(target, None)
            self.cart = {k: v for k, v in self.cart.items() if v['user_id'] != target}
            for order in self.orders.values():
                if order['user_id'] == target:
                    order['user_id'] = None
            for access, record in list(self.access.items()):
                if record['uid'] == target:
                    self.access.pop(access)
                    self.refresh.pop(record['refresh'], None)
            return httpx.Response(200, json={})
        if path.startswith('/rest/v1/rpc/'):
            return self.rpc(path.rsplit('/', 1)[-1], body, uid, admin)
        name = path.rsplit('/', 1)[-1]
        if name == 'products':
            rows = [p.copy() for p in self.products.values() if p['is_active']]
        elif not uid:
            return self.error('AUTH_REQUIRED', 401)
        elif name == 'users':
            rows = [self.profile(uid)] if uid in self.users else []
        elif name == 'cart_items':
            rows = [v.copy() for v in self.cart.values() if v['user_id'] == uid]
        elif name == 'orders':
            rows = [v.copy() for v in self.orders.values() if v['user_id'] == uid]
        elif name in ('order_items', 'payments'):
            source = self.items if name == 'order_items' else self.payments
            rows = [v.copy() for v in source.values() if self.orders[v['order_id']]['user_id'] == uid]
        else:
            return self.error('Not found', 404)
        for key, value in params.items():
            if value.startswith('eq.'):
                expected = value[3:]
                rows = [r for r in rows if str(r.get(key)).lower() == expected.lower()]
        if method == 'PATCH':
            for row in rows:
                target = self.users[row['id']] if name == 'users' else self.cart[row['id']]
                target.update(body)
                row.update(body)
        elif method == 'DELETE' and name == 'cart_items':
            for row in rows:
                self.cart.pop(row['id'], None)
        if name == 'cart_items' and 'product:' in params.get('select', ''):
            for row in rows:
                product = self.products.get(row['product_id'])
                row['product'] = product.copy() if product and product['is_active'] else None
        order_by = params.get('order', 'id.asc')
        rows.sort(key=lambda r: (r.get('created_at', ''), r['id']) if 'created_at' in order_by else r['id'], reverse='desc' in order_by)
        offset, limit = int(params.get('offset', 0)), int(params.get('limit', len(rows)))
        return httpx.Response(200, json=rows[offset:offset + limit])

    def rpc(self, name, body, uid, admin):
        if name == 'pay_mock_order':
            if not admin:
                return self.error('Forbidden', 403)
            uid = body.get('p_user_id')
        if not uid or uid not in self.users:
            return self.error('AUTH_REQUIRED', 401)
        if name == 'add_cart_item':
            product = self.products.get(body['p_product_id'])
            if not product or not product['is_active']:
                return self.error('PRODUCT_INACTIVE')
            row = next((v for v in self.cart.values() if v['user_id'] == uid and v['product_id'] == product['id']), None)
            quantity = body['p_quantity'] + (row['quantity'] if row else 0)
            if quantity > product['stock']:
                return self.error('INSUFFICIENT_STOCK')
            if row:
                row['quantity'] = quantity
            else:
                row = dict(id=str(uuid4()), user_id=uid, product_id=product['id'], quantity=quantity)
                self.cart[row['id']] = row
            return httpx.Response(200, json=row)
        order_id = body.get('p_order_id')
        order = self.orders.get(order_id)
        if name == 'create_order':
            quantities = {}
            for item in body['p_items']:
                quantities[item['product_id']] = quantities.get(item['product_id'], 0) + item['quantity']
            if order:
                old = {v['product_id']: v['quantity'] for v in self.items.values() if v['order_id'] == order_id}
                if order['user_id'] != uid or old != quantities or any(order[key] != body['p_' + key]
                    for key in ('recipient_name', 'recipient_phone', 'shipping_address')) or order['total_amount'] != body['p_expected_total']:
                    return self.error('IDEMPOTENCY_CONFLICT')
                return httpx.Response(200, json=order)
            total, items = 0, []
            for product_id, quantity in quantities.items():
                product = self.products.get(product_id)
                if not product:
                    return self.error('PRODUCT_NOT_FOUND')
                if not product['is_active']:
                    return self.error('PRODUCT_INACTIVE')
                if product['stock'] < quantity:
                    return self.error('INSUFFICIENT_STOCK')
                total += product['price'] * quantity
                items.append(dict(id=str(uuid4()), order_id=order_id, product_id=product_id,
                    product_name=product['name'], unit_price=product['price'], quantity=quantity))
            if total != body['p_expected_total']:
                return self.error('PRICE_CHANGED')
            order = dict(id=order_id, user_id=uid, status='pending', total_amount=total,
                recipient_name=body['p_recipient_name'], recipient_phone=body['p_recipient_phone'],
                shipping_address=body['p_shipping_address'], created_at=now())
            self.orders[order_id] = order
            self.items.update({v['id']: v for v in items})
            return httpx.Response(200, json=order)
        if not order:
            return self.error('ORDER_NOT_FOUND')
        if order['user_id'] != uid:
            return self.error('ORDER_FORBIDDEN', 403)
        if name == 'cancel_order':
            if order['status'] == 'paid':
                return self.error('PAID_ORDER_CANNOT_CANCEL')
            order['status'] = 'cancelled'
            return httpx.Response(200, json=order)
        if name == 'pay_mock_order':
            payment = self.payments.get(order_id)
            if order['status'] == 'paid':
                return httpx.Response(200, json={'order': order, 'payment': payment})
            if order['status'] != 'pending':
                return self.error('ORDER_NOT_PAYABLE')
            items = [v for v in self.items.values() if v['order_id'] == order_id]
            failed = next(('PRODUCT_INACTIVE' if not self.products[v['product_id']]['is_active'] else 'INSUFFICIENT_STOCK'
                for v in items if not self.products[v['product_id']]['is_active'] or self.products[v['product_id']]['stock'] < v['quantity']), None)
            if not body.get('p_should_succeed', True):
                failed = 'MOCK_PAYMENT_DECLINED'
            payment = payment or dict(id=str(uuid4()), order_id=order_id, amount=order['total_amount'])
            payment.update(status='failed' if failed else 'succeeded', paid_at=None if failed else now())
            self.payments[order_id] = payment
            if failed:
                return httpx.Response(200, json={'order': order, 'payment': payment, 'failure_code': failed})
            for item in items:
                self.products[item['product_id']]['stock'] -= item['quantity']
            order['status'] = 'paid'
            return httpx.Response(200, json={'order': order, 'payment': payment})
        return self.error('Unknown RPC', 404)
