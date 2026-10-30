# 테이블 정의서

[문서 목록](README.md) · [ERD](erd.md) · [구매 시뮬레이션](purchase-simulation.md)

## 공통 규칙

- 업무 테이블은 모두 `public` 스키마에 생성합니다.
- PK는 기본키, FK는 외래키, UNIQUE는 중복 불가입니다.
- NULL 허용 표시가 없는 컬럼은 모두 필수입니다.
- `users.id` 외의 PK는 `uuid`이며 기본값은 `gen_random_uuid()`입니다.
- 금액은 원화 정수 `bigint`, 시각은 `timestamptz`로 저장합니다.
- 생성 시각 기본값은 `now()`입니다.

## 1. users — 회원

| 컬럼 | 타입 | 제약·기본값 | 설명 |
|---|---|---|---|
| id | uuid | PK, FK → auth.users.id | 인증 계정과 같은 ID |
| name | varchar(100) | 필수 | 회원 이름 |
| phone | varchar(30) | NULL 허용 | 연락처 |
| created_at | timestamptz | now() | 가입 시각 |

이메일·비밀번호는 Supabase Auth가 관리하며 이 테이블에 중복 저장하지 않습니다. 가입 시 프로필을 함께 생성합니다. 로그인·로그아웃은 인증 세션 처리이며 이 테이블에 행을 추가하지 않습니다.

## 2. products — 상품

| 컬럼 | 타입 | 제약·기본값 | 설명 |
|---|---|---|---|
| id | uuid | PK | 상품 ID |
| name | varchar(200) | 필수 | 상품명 |
| description | text | 기본값 빈 문자열 | 상품 설명 |
| price | bigint | CHECK price >= 0 | 판매가 |
| stock | integer | 기본값 0, CHECK stock >= 0 | 현재 재고 |
| image_url | text | NULL 허용 | 대표 이미지 |
| is_active | boolean | 기본값 true | 판매 여부 |

상품 목록은 판매 중인 상품을 표시하고 재고 0은 품절로 표시합니다. 주문된 상품은 물리 삭제하지 않고 `is_active=false`로 판매를 중지합니다.

## 3. cart_items — 장바구니 항목

| 컬럼 | 타입 | 제약·기본값 | 설명 |
|---|---|---|---|
| id | uuid | PK | 장바구니 항목 ID |
| user_id | uuid | FK → users.id | 소유 회원 |
| product_id | uuid | FK → products.id | 상품 |
| quantity | integer | CHECK quantity > 0 | 담은 수량 |

`UNIQUE(user_id, product_id)`를 적용합니다. 같은 상품을 다시 담으면 기존 수량을 늘립니다. 가격은 `products.price`에서 읽고 장바구니에 저장하지 않습니다.

## 4. orders — 주문

| 컬럼 | 타입 | 제약·기본값 | 설명 |
|---|---|---|---|
| id | uuid | PK | 주문 ID |
| user_id | uuid | FK → users.id, NULL 허용 | 주문 회원, 탈퇴 시 NULL |
| status | varchar(20) | 기본값 pending | pending / paid / cancelled |
| total_amount | bigint | CHECK total_amount >= 0 | 주문 항목 금액의 합 |
| recipient_name | varchar(100) | 필수 | 수령인 |
| recipient_phone | varchar(30) | 필수 | 배송 연락처 |
| shipping_address | text | 필수 | 우편번호·상세 주소를 포함한 배송 주소 |
| created_at | timestamptz | now() | 주문 시각 |

신규 주문은 반드시 로그인 회원으로 생성합니다. `user_id`의 NULL 허용은 탈퇴 이후 기록 보존을 위한 것입니다. 배송정보는 주문 당시 값으로 저장합니다.

주문 상태는 `pending → paid` 또는 `pending → cancelled`입니다. 결제 실패 시에는 `pending`을 유지하여 재시도할 수 있습니다. 결제된 주문의 취소·환불은 이번 최소 범위에 포함하지 않습니다.

## 5. order_items — 주문 항목

| 컬럼 | 타입 | 제약·기본값 | 설명 |
|---|---|---|---|
| id | uuid | PK | 주문 항목 ID |
| order_id | uuid | FK → orders.id | 소속 주문 |
| product_id | uuid | FK → products.id | 원본 상품 |
| product_name | varchar(200) | 필수 | 주문 당시 상품명 |
| unit_price | bigint | CHECK unit_price >= 0 | 주문 당시 단가 |
| quantity | integer | CHECK quantity > 0 | 주문 수량 |

`UNIQUE(order_id, product_id)`를 적용하고 동일 상품은 한 행으로 합칩니다. 항목 금액은 `unit_price × quantity`로 계산하므로 별도 합계 컬럼은 두지 않습니다.

## 6. payments — 결제

| 컬럼 | 타입 | 제약·기본값 | 설명 |
|---|---|---|---|
| id | uuid | PK | 결제 ID |
| order_id | uuid | FK → orders.id, UNIQUE | 주문당 결제 한 행 |
| amount | bigint | CHECK amount >= 0 | 주문과 같은 금액 |
| status | varchar(20) | 기본값 pending | pending / succeeded / failed |
| paid_at | timestamptz | NULL 허용 | 성공 시각 |

첫 시도에서 생성하고, 실패 후 재시도는 같은 행을 갱신합니다. `failed → pending → succeeded/failed`를 허용하며 `succeeded`는 다시 처리하지 않습니다. `paid_at`은 성공 상태에서만 값을 갖도록 CHECK를 적용합니다.

## 삭제 규칙

| 부모 → 자식 | 삭제 동작 |
|---|---|
| auth.users → users | CASCADE: 회원 프로필 삭제 |
| users → cart_items | CASCADE: 장바구니 삭제 |
| users → orders | SET NULL: 주문 기록 보존 |
| products → cart_items | CASCADE: 장바구니에서 제거 |
| products → order_items | RESTRICT: 주문된 상품의 물리 삭제 금지 |
| orders → order_items / payments | RESTRICT: 거래 기록의 직접 삭제 방지 |

회원 탈퇴는 본인 확인 후 서버에서 수행합니다. 주문의 배송 개인정보는 별도 보존·익명화 정책을 정한 뒤 처리하며, 탈퇴 시 즉시 모두 삭제된다고 가정하지 않습니다.

## 서버·DB에서 보장할 핵심 규칙

1. 본인 프로필·장바구니·주문·결제만 접근하도록 인증과 RLS를 적용합니다. 상품은 공개 조회만 허용합니다.
2. 주문금액은 클라이언트 값을 신뢰하지 않고 현재 상품 가격으로 서버가 계산합니다.
3. 주문과 한 개 이상의 주문 항목은 하나의 DB 트랜잭션으로 생성합니다.
4. 주문 생성 이후 항목과 금액은 수정하지 않습니다. 변경하려면 미결제 주문을 취소하고 새로 만듭니다.
5. 모의 결제 확정은 주문·상품 행 잠금, 상태·재고 확인, 재고 차감, 결제 성공, 주문 완료를 한 트랜잭션에서 처리합니다. 상품은 ID 순서로 잠급니다.
6. `payments.amount = orders.total_amount` 및 주문 합계 일치는 처리 함수에서 검증합니다. 서로 다른 테이블의 합계는 단순 CHECK만으로 보장하지 않습니다.
7. 같은 주문의 결제 재요청은 기존 성공 결과를 반환하여 중복 차감을 막습니다. 결제 상태 직접 수정은 클라이언트에 허용하지 않습니다.
8. 주문 생성 요청의 `orders.id`를 요청 식별자로 재사용합니다. 같은 ID의 같은 요청은 기존 주문을 반환하고, 내용이 다르면 충돌 오류를 반환합니다. ID는 권한 증명이 아니므로 소유권을 별도 확인합니다.

조회용 인덱스는 `orders(user_id, created_at)`, `order_items(order_id)`를 두고 UNIQUE 제약의 인덱스도 활용합니다.
