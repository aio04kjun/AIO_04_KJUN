# ERD에 맞춘 SQL 적용 안내

[문서 목록](README.md) · [테이블 정의](table-definition.md) · [기존 SQL 검토 기록](sql-review.md)

## 변경 결과

기존 ERD의 6개 테이블과 컬럼·타입·관계·상태를 기준으로 SQL을 수정했습니다.

| 항목 | 수정 내용 |
|---|---|
| users | Supabase Auth의 ID를 참조. 이메일·password_hash·자체 탈퇴 플래그 제거 |
| products | bigint 금액, image_url·is_active 추가. 상품명·재고 검증 유지 |
| cart_items | 별도 테이블로 분리. 회원·상품 조합 UNIQUE |
| orders | pending / paid / cancelled. 필수 배송정보, 탈퇴 시 user_id=NULL |
| order_items | 주문 당시 상품명·단가 저장. 동일 주문·상품 UNIQUE |
| payments | 주문당 한 행. pending / succeeded / failed. 성공 시각 저장 |
| 인덱스 | 회원별 주문 조회·상품 FK 인덱스 유지. 주문별 조회는 UNIQUE 인덱스 활용 |
| seed.sql | 기존 상품 5개·가격·재고·고정 ID·재실행 시 덮어쓰기 방지 유지 |

무료 상품도 허용하는 기존 ERD에 맞춰 금액 CHECK는 `>= 0`입니다. image_url 기본값은 NULL이며 프론트엔드에서 대체 이미지를 표시합니다. 시드 상품은 모두 판매 상태이며 노트는 재고 0인 품절입니다.

## 실행 순서

1. **신규 개발용 Supabase 프로젝트**의 SQL Editor에서 [schema.sql](../sql/schema.sql)을 실행합니다.
2. 이어서 [seed.sql](../sql/seed.sql)을 실행합니다.
3. Step 2 API용 [backend-functions.sql](../sql/backend-functions.sql)을 실행합니다. 회원·상품별 장바구니 수량을 원자적으로 증가시키는 add_cart_item RPC입니다. 재실행할 수 있습니다.
4. Supabase Auth로 테스트 회원을 가입시키면 public.users 프로필이 자동 생성됩니다. 설치 전 만들어 둔 인증 계정은 설치 시 프로필을 생성합니다.
5. 별도 개발 DB에서 테스트 계정 2개 이상을 준비한 뒤 [verify.sql](../sql/verify.sql)을 실행합니다.

schema.sql은 기존 테이블을 변경하는 마이그레이션 파일이 아닙니다. 이미 이전 SQL을 실행한 DB에서는 그대로 재실행하지 마세요. 기존 데이터의 유무를 확인한 뒤 별도 마이그레이션이 필요합니다. 이번 작업에서는 원격 DB에 접속하거나 실행하지 않았습니다.

## FastAPI에서 호출할 DB 함수

### create_order — 주문 생성

사용자 JWT가 설정된 Supabase 클라이언트로 호출합니다. 함수 내부에서 `auth.uid()`를 확인하므로 사용자 ID를 입력받아 신뢰하지 않습니다.

```json
{
  "p_order_id": "20000000-0000-4000-8000-000000000001",
  "p_items": [
    {"product_id": "10000000-0000-4000-8000-000000000003", "quantity": 2},
    {"product_id": "10000000-0000-4000-8000-000000000002", "quantity": 1}
  ],
  "p_recipient_name": "김하늘",
  "p_recipient_phone": "010-0000-0000",
  "p_shipping_address": "01234 서울시 예제구 예제로 1, 101호",
  "p_expected_total": 39000
}
```

- 장바구니 구매는 화면에서 선택한 상품 ID·수량을 고정하여 FastAPI에 전달하고 p_items를 구성합니다. 바로 구매도 같은 함수를 사용합니다. 가격·재고·로그인 회원은 DB에서 검증합니다. 재요청 시에는 장바구니를 다시 읽어 내용을 바꾸지 않고 기존 요청값을 그대로 사용합니다.
- 항목은 1~100개까지 입력하며 같은 상품은 수량을 합산합니다. 수량은 양의 정수입니다.
- DB가 최신 상품 가격으로 계산한 총액과 화면에서 확인한 p_expected_total을 비교합니다. 다르면 `PRICE_CHANGED` 오류를 반환하므로 최신 가격을 표시하고 다시 확인받습니다.
- 주문과 항목을 한 트랜잭션으로 저장합니다. 상품명과 단가는 이 시점 값으로 고정합니다.
- 재고는 확인만 하고 예약하거나 차감하지 않습니다. 장바구니도 유지합니다.
- 같은 p_order_id·같은 내용을 재요청하면 기존 주문을 반환합니다. 다른 내용은 `IDEMPOTENCY_CONFLICT`입니다. 신규 주문에는 새 ID를 사용합니다.

### pay_mock_order — 모의 결제 확정

**FastAPI의 서버 전용 service_role 클라이언트로만 호출합니다.** 사용자 JWT로는 실행할 수 없습니다. 서버가 로그인 토큰에서 검증한 ID를 p_user_id에 넣어야 하며, 클라이언트가 보낸 임의 회원 ID를 사용하면 안 됩니다.

```json
{
  "p_order_id": "20000000-0000-4000-8000-000000000001",
  "p_user_id": "검증된 로그인 회원의 UUID",
  "p_should_succeed": true
}
```

- p_should_succeed=false는 개발 중 결제 실패를 재현하는 옵션입니다. 실제 PG 결제가 아닙니다.
- 주문을 잠그고 상품을 UUID 순서로 잠근 뒤, 소유권·상태·금액·판매 상태·재고를 확인합니다.
- 성공 시 재고 차감·결제 succeeded·paid_at 기록·주문 paid를 같은 트랜잭션에서 처리합니다.
- 모의 거절·판매 중지·재고 부족은 결제 failed를 저장하고 주문 pending·재고 유지를 보장합니다. 예외 대신 결과 JSON의 failure_code를 반환합니다.
- 실패 후 재시도는 같은 결제 행을 갱신합니다. 이미 성공한 주문의 재요청은 기존 성공 결과를 반환하여 중복 차감을 막습니다.
- 성공 응답 후 프론트엔드가 완료 안내와 함께 상품 목록으로 이동해야 합니다. SQL은 화면 이동을 처리하지 않습니다.

### cancel_order — 미결제 주문 취소

사용자 JWT로 `{"p_order_id":"주문 UUID"}`를 전달합니다. 본인의 pending 주문만 취소할 수 있고, 이미 취소된 주문의 재요청도 cancelled를 반환합니다. paid 주문은 거부합니다. 재고를 예약하지 않으므로 복원하지 않습니다.

## 접근 권한과 탈퇴

- 익명·로그인 사용자는 판매 중인 상품을 읽을 수 있습니다. 브라우저의 앱 데이터 요청은 기존 계획대로 FastAPI를 거치도록 구현합니다.
- 로그인 사용자는 본인 프로필·장바구니·주문·항목·결제만 조회할 수 있습니다.
- 프로필은 name·phone만 수정할 수 있습니다. 장바구니는 본인 항목을 추가·수량 수정·삭제할 수 있습니다.
- 주문·항목·결제 직접 쓰기는 일반 사용자에게 허용하지 않습니다. 주문·취소는 RPC, 결제는 서버 전용 RPC로 처리합니다.
- SECURITY DEFINER 함수는 고정된 빈 search_path와 명시적 스키마를 사용하며, 기본 PUBLIC 실행 권한을 제거했습니다.
- 서버 관리자 키는 RLS를 우회하므로 API도 사용자·리소스 소유권을 검증해야 합니다.
- 탈퇴는 서버가 Supabase Auth 계정을 삭제하는 단계에서 처리합니다. FK에 따라 프로필·장바구니는 삭제되고 주문 회원 ID는 NULL이 됩니다. 주문·결제는 보존됩니다. 배송 개인정보의 보존·익명화 정책은 별도 적용해야 합니다.

## 검증 범위

PostgreSQL 파서(pglast)로 다음 정적 검사를 통과했습니다.

| 검사 대상 | 결과 |
|---|---|
| schema.sql | SQL 구문 46개·PL/pgSQL 함수 4개 문법 통과 |
| seed.sql | SQL 구문 3개 문법 통과 |
| verify.sql | SQL 구문 17개·PL/pgSQL 블록 5개 문법 통과 |
| erd.mmd와 스키마 비교 | 6개 테이블의 모든 컬럼명·타입 일치 |
| 접근 제어 및 문서 | 모든 테이블 RLS 설정·로컬 문서 링크 확인 |

검사 코드는 [check_sql.py](../tests/check_sql.py)입니다. pglast는 SQL 검사용 Python 개발 도구이며 쇼핑몰 실행 의존성이나 프론트엔드 라이브러리가 아닙니다.

verify.sql은 주문 재요청·구매 당시 가격·결제 실패/재시도·중복 차감·재고 부족·타 회원 RLS·주문 취소·장바구니 유지를 검사하는 개발 DB용 스크립트이며 마지막에 ROLLBACK합니다. 이 스크립트의 문법 검사와 실제 DB에서의 동작 검증은 서로 다릅니다.

이후 사용자의 Supabase 연결 요청에 따라 config.json으로 원격 DB에 설치하고 verify.sql의 실제 DB 검증을 통과했습니다. 테스트 데이터는 모두 롤백했습니다. 자세한 진행 상태는 [Supabase 연결 상태](supabase-connection.md)를 참고하세요. 배포 전 두 연결에서 같은 주문 결제 및 마지막 재고 동시 구매를 실행해 한 번만 차감되는지도 확인해야 합니다.
