# 쇼핑몰 API 명세 — Step 2

[실행 안내](../README.md) · [백엔드 구조](backend.md) · [SQL](sql-application.md)

## 공통 계약

- 기본 경로: `/api/v1`
- 요청·응답: JSON. 모든 POST·PATCH·DELETE는 Content-Type: application/json을 사용합니다.
- 본문에 필드가 없는 작업도 `{}`를 보냅니다. 정의되지 않은 입력 필드는 거부합니다.
- 변경 요청은 shop_csrf 쿠키와 같은 X-CSRF-Token 헤더가 필요합니다. 로그인·가입도 동일합니다.
- 인증은 HttpOnly 쿠키입니다. 브라우저 fetch는 같은 출처에서 `credentials: 'same-origin'`을 사용합니다.
- 성공: `{"data": ...}`. 목록은 pagination을 함께 반환합니다.
- 오류: `{"error":{"code":"AUTH_REQUIRED","message":"로그인이 필요합니다."}}`
- 금액은 원화 정수, ID는 UUID, 시각은 ISO 8601입니다.
- API는 HTML 로그인 페이지로 302 이동하지 않습니다. 401을 받은 프론트엔드가 화면 이동을 처리합니다.

## 엔드포인트 목록

변경 요청은 아래 표의 로그인 여부와 관계없이 모두 CSRF가 필요합니다.

| Method | 경로 | 로그인 | 성공 HTTP | 용도 |
|---|---|---|---:|---|
| GET | /auth/csrf | 불필요 | 200 | CSRF 발급 |
| GET | /config | 불필요 | 200 | 체험 모드·모의 결제 공개 플래그 |
| POST | /auth/signup | 불필요 | 201 | 회원가입 |
| POST | /auth/login | 불필요 | 200 | 로그인·next 검증 |
| POST | /auth/refresh | refresh 쿠키 | 200 | 세션 갱신 |
| POST | /auth/logout | 선택 | 200 | 현재 세션 로그아웃 |
| GET | /users/me | 필요 | 200 | 회원정보 |
| PATCH | /users/me | 필요 | 200 | 이름·연락처 수정 |
| DELETE | /users/me | 필요 | 200 | 비밀번호 재확인 후 탈퇴 |
| GET | /products | 불필요 | 200 | 상품 목록 |
| GET | /products/{product_id} | 불필요 | 200 | 상품 상세 |
| GET | /cart | 필요 | 200 | 장바구니·현재 금액 |
| POST | /cart/items | 필요 | 201 | 상품 담기·기존 수량 증가 |
| PATCH | /cart/items/{item_id} | 필요 | 200 | 절대 수량 변경 |
| DELETE | /cart/items/{item_id} | 필요 | 200 | 한 항목 삭제 |
| DELETE | /cart | 필요 | 200 | 장바구니 비우기 |
| POST | /orders | 필요 | 200 | 주문 생성·동일 요청 재시도 |
| GET | /orders | 필요 | 200 | 내 주문 목록 |
| GET | /orders/{order_id} | 필요 | 200 | 항목·결제를 포함한 주문 상세 |
| POST | /orders/{order_id}/cancel | 필요 | 200 | 미결제 취소 |
| POST | /orders/{order_id}/pay | 필요 | 200 | 모의 결제 시도 |

별도로 GET `/health`는 프로세스 상태 `{"data":{"status":"ok"}}`를 반환합니다. 실제 DB 연결 확인용 상태 점검은 아닙니다.

GET `/config`는 `{"data":{"demo_mode":false,"mock_payments_enabled":true}}` 형식으로 공개 설정만 반환합니다. API 키를 포함하지 않습니다. 화면의 `/cart`, `/checkout`, `/mypage` 경로는 별도 HTML 경로이며 게스트 진입 시 next를 보존한 303 로그인 이동을 수행합니다.

## 1. 인증

### CSRF 발급

GET `/auth/csrf`

```json
{"data":{"csrf_token":"발급된-임의-토큰"}}
```

브라우저 쿠키와 함께 토큰을 보관합니다. 기존의 유효한 CSRF 쿠키가 있으면 재사용합니다.

### 회원가입

POST `/auth/signup`

```json
{"email":"test@example.com","password":"your-test-password","name":"김하늘"}
```

- 이메일은 공백 제거·소문자로 정규화합니다.
- 비밀번호 8~128자, 이름 1~100자입니다. Supabase 프로젝트에 설정된 추가 비밀번호 정책도 적용됩니다.
- 이메일 인증 설정에 따라 signed_in 값이 달라집니다.

```json
{"data":{"signed_in":false,"message":"가입 요청을 처리했습니다. 이메일 인증이 설정된 경우 메일을 확인해 주세요."}}
```

signed_in=true일 때는 인증 쿠키도 설정됩니다. JSON에 access·refresh 토큰을 노출하지 않습니다.

### 로그인

POST `/auth/login`

```json
{"email":"test@example.com","password":"your-test-password","next":"/checkout?product_id=10000000-0000-4000-8000-000000000003&quantity=2"}
```

```json
{"data":{"next":"/checkout?product_id=10000000-0000-4000-8000-000000000003&quantity=2","expires_in":3600}}
```

next 생략 시 `/`입니다. 상품·장바구니·결제·마이페이지의 허용된 내부 화면만 통과시키고, 외부 주소·이중 슬래시·역슬래시·제어문자·로그인 페이지 등은 `/`로 대체합니다.

### 갱신·로그아웃

POST `/auth/refresh`, POST `/auth/logout`의 본문은 `{}`입니다.

- 갱신: `{"data":{"expires_in":3600}}`, 인증 쿠키 교체
- 로그아웃: `{"data":{"message":"로그아웃했습니다."}}`, 인증 쿠키 삭제
- 갱신 실패: 401 AUTH_REQUIRED. 재로그인이 필요합니다.

## 2. 회원

GET `/users/me`는 회원 프로필에 인증 계정의 이메일을 합쳐 반환합니다.

```json
{"data":{"id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","name":"김하늘","phone":null,"created_at":"2026-10-29T00:00:00Z","email":"test@example.com"}}
```

PATCH `/users/me`는 name·phone 중 하나 이상을 받습니다. phone=null은 연락처 삭제입니다. id·이메일·비밀번호를 이 요청으로 변경할 수 없습니다.

```json
{"name":"김하늘","phone":"010-0000-0000"}
```

DELETE `/users/me`는 `{"password":"현재 비밀번호"}`를 받습니다. 성공 시 회원 탈퇴 안내 JSON과 쿠키 삭제를 반환합니다. 주문 기록은 유지되고 user_id만 NULL이 됩니다.

## 3. 상품

GET `/products?page=1&page_size=12`

- page: 1~100000, 기본 1
- page_size: 1~100, 기본 12
- 판매 중인 상품을 ID 순서로 조회합니다. stock=0인 상품도 품절 표시를 위해 반환합니다.

```json
{
  "data":[{"id":"10000000-0000-4000-8000-000000000003","name":"데일리 머그컵","description":"기본 머그컵","price":12000,"stock":15,"image_url":null,"is_active":true}],
  "pagination":{"page":1,"page_size":12,"has_more":false}
}
```

GET `/products/{product_id}`는 data에 상품 객체 하나를 반환합니다. 판매 중지가 되었거나 없는 상품은 404입니다.

## 4. 장바구니

POST `/cart/items`

```json
{"product_id":"10000000-0000-4000-8000-000000000003","quantity":2}
```

같은 상품은 원자적으로 기존 수량에 더합니다. 수량은 양의 정수이며 재고를 초과하면 409입니다. 성공 시 data는 cart_items 한 행입니다.

PATCH `/cart/items/{item_id}`의 `{"quantity":3}`은 기존 수량에 더하지 않고 **3개로 변경**합니다.

GET `/cart` 응답 예시:

```json
{
  "data":{
    "items":[{
      "id":"30000000-0000-4000-8000-000000000001",
      "user_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      "product_id":"10000000-0000-4000-8000-000000000003",
      "quantity":2,
      "product":{"id":"10000000-0000-4000-8000-000000000003","name":"데일리 머그컵","price":12000,"stock":15,"image_url":null,"is_active":true},
      "available":true,
      "subtotal":24000
    }],
    "total_amount":24000
  }
}
```

판매 중지 상품은 RLS에 의해 product=null, available=false, subtotal=0으로 표시됩니다. 재고가 수량보다 적으면 available=false입니다. 표시 총액은 현재 조회 가능한 상품 금액의 합이며 결제 보장 금액이 아닙니다.

DELETE `/cart/items/{item_id}`, DELETE `/cart`는 `{}`를 전송하고 `{"data":{"deleted":true}}`를 받습니다.

## 5. 주문

POST `/orders`

```json
{
  "order_id":"20000000-0000-4000-8000-000000000001",
  "items":[
    {"product_id":"10000000-0000-4000-8000-000000000003","quantity":2},
    {"product_id":"10000000-0000-4000-8000-000000000002","quantity":1}
  ],
  "recipient_name":"김하늘",
  "recipient_phone":"010-0000-0000",
  "shipping_address":"01234 서울시 예제구 예제로 1, 101호",
  "expected_total":39000
}
```

- items: 1~100개, 같은 상품은 DB에서 수량 합산
- 수량: 1~2147483647 정수. bool·소수·문자열 수량은 거부
- 주문금액: DB가 계산하며 expected_total과 다르면 PRICE_CHANGED
- order_id: 클라이언트가 새 UUID를 생성하고 같은 요청 재시도에 재사용
- 장바구니 구매는 선택된 상품·수량을 items에 넣습니다. 바로 구매도 같은 형식입니다.
- 재시도에는 전체 요청 본문을 유지합니다. 장바구니를 다시 읽어 items를 바꾸지 않습니다.
- 상품별 단가·회원 ID·주문 상태는 입력받지 않습니다.
- 성공 data는 orders 한 행이며 기본 status=pending입니다. 재고와 장바구니는 유지합니다.

GET `/orders?page=1&page_size=10&status=paid`는 본인 주문만 반환합니다. status는 pending / paid / cancelled 중 하나이며 생략 시 전체 주문입니다. 구매 내역 화면은 paid를 사용합니다. pagination은 상품 목록과 같은 구조입니다.

GET `/orders/{order_id}`는 orders 필드에 items 배열과 payment 객체 또는 null을 추가합니다. 주문 항목은 구매 당시 상품명·단가입니다. 타 회원 주문은 404입니다.

POST `/orders/{order_id}/cancel`은 `{}`를 받습니다. 본인의 pending 주문을 cancelled로 변경하고 주문 객체를 반환합니다. 이미 취소된 주문은 같은 결과를 반환하며 paid는 409입니다.

## 6. 모의 결제

POST `/orders/{order_id}/pay`, 본문 `{}`

```json
{
  "data":{
    "order":{"id":"20000000-0000-4000-8000-000000000001","status":"paid","total_amount":39000},
    "payment":{"id":"결제 UUID","order_id":"20000000-0000-4000-8000-000000000001","amount":39000,"status":"succeeded","paid_at":"2026-10-29T00:00:00Z"}
  }
}
```

order에는 위 예시 외 나머지 주문 필드도 포함됩니다. 결제 RPC는 서버 관리자 권한으로 실행하지만 회원 ID는 서버가 검증한 로그인 계정에서 가져옵니다.

**HTTP 200만으로 결제 성공을 판단하지 마세요.** 결제 시도를 처리했으나 재고가 부족하면 아래처럼 반환합니다.

```json
{"data":{"order":{"status":"pending"},"payment":{"status":"failed"},"failure_code":"INSUFFICIENT_STOCK"}}
```

성공 조건은 `data.payment.status === 'succeeded'`와 `data.order.status === 'paid'`입니다. 성공 시에만 완료 안내 후 상품 목록으로 이동합니다. 실패는 같은 주문으로 다시 시도할 수 있습니다. 이미 성공한 주문은 기존 결과를 반환합니다.

ENABLE_MOCK_PAYMENTS=false이면 503 MOCK_PAYMENTS_DISABLED입니다. 실패 재현 옵션 p_should_succeed는 외부 API에서 받지 않습니다. 개발 SQL에서 직접 RPC의 false 옵션을 사용할 수 있습니다.

## 오류 코드

| HTTP | 코드 예시 | 처리 |
|---:|---|---|
| 400 | AUTH_FAILED | 가입 입력·이메일 설정 확인 |
| 401 | AUTH_REQUIRED / INVALID_CREDENTIALS / INVALID_PASSWORD | 갱신 또는 로그인·비밀번호 확인 |
| 403 | CSRF_FAILED / FORBIDDEN | CSRF 재발급·권한 확인 |
| 404 | NOT_FOUND | 삭제·판매 중지·접근 불가 대상 안내 |
| 409 | PRICE_CHANGED / INSUFFICIENT_STOCK / IDEMPOTENCY_CONFLICT | 금액·수량·요청 ID 재확인 |
| 415 | JSON_REQUIRED | JSON Content-Type 설정 |
| 422 | VALIDATION_ERROR | 필드 오류 표시. details에 field·message 포함 |
| 429 | RATE_LIMITED | 잠시 후 재시도 |
| 502 / 503 | UPSTREAM_ERROR / UPSTREAM_UNAVAILABLE | 공급자 장애 안내 후 재시도 |
| 500 | INTERNAL_ERROR | 서버 오류 안내 |

오류 응답에는 비밀번호·토큰·원본 SQL 메시지를 포함하지 않습니다.
