# 쇼핑몰 최소 설계 — Step 1

회원가입·로그인·회원정보 수정·탈퇴, 상품 조회, 장바구니, 주문, 모의 결제, 구매 내역에 필요한 최소 설계입니다.

## 문서 읽는 순서

1. [ERD와 테이블 관계](erd.md)
2. [테이블 정의서](table-definition.md)
3. [상품 구매 시뮬레이션](purchase-simulation.md)
4. [SQL 적용 검토](sql-review.md)
5. [수정된 SQL 적용 안내](sql-application.md)
6. [Step 2 실행 안내](../README.md) · [API 명세](api-spec.md) · [백엔드 구조](backend.md)
7. [Step 3 실행·구매 확인](run-guide.md) · [화면·소스 안내](frontend.md)

[테이블 ERD 이미지(PNG)](erd-tables.png) · [확대용 ERD(SVG)](erd-tables.svg)

[상품 구매 시뮬레이션 이미지(PNG)](purchase-simulation.png) · [확대용 구매 시뮬레이션(SVG)](purchase-simulation.svg)

ERD 원본은 [erd.mmd](erd.mmd)입니다. `erd.md`에는 같은 내용을 Mermaid 코드 블록으로 넣어 Mermaid 지원 Markdown 미리보기에서 그림으로 볼 수 있습니다. `.mmd` 링크만으로 그림이 표시되지는 않습니다. VSCode에서는 Mermaid를 지원하는 Markdown 미리보기를 사용하세요.

## 최소화한 범위

- 테이블은 회원, 상품, 장바구니 항목, 주문, 주문 항목, 결제의 6개입니다.
- 장바구니 전용 헤더 테이블 없이 `cart_items.user_id`로 소유자를 구분합니다.
- 주문 하나에 결제 레코드 하나를 사용하며, 실패 후 재시도는 같은 레코드를 갱신합니다.
- 결제는 모의 결제입니다. 실제 PG 결제와 결제 시도별 이력은 후속 확장 범위입니다.
- 통화는 원화, 배송비는 0원입니다. 옵션·쿠폰·환불·배송 추적은 포함하지 않습니다.
- 재고는 결제 성공 시 차감하며, 주문 단계에서는 예약하지 않습니다.
- 비밀번호와 이메일은 Supabase Auth가 관리합니다.

## 프로젝트 구조

```text
shopping-mall/
├── docs/
│   ├── README.md
│   ├── erd.md
│   ├── erd.mmd
│   ├── table-definition.md
│   └── purchase-simulation.md
├── app/
│   ├── main.py                 # FastAPI·HTML 경로·정적 파일
│   ├── config.py               # 환경변수
│   ├── supabase_client.py      # Supabase 연결
│   ├── auth.py                 # 인증·현재 회원·next 검증
│   ├── schemas.py              # JSON 입력·출력 검증
│   ├── errors.py               # API 오류
│   ├── web.py                  # HTML 경로·보호 화면·정적 파일
│   ├── demo.py                 # 로컬 메모리 체험
│   ├── routers/                # auth, users, products, cart, orders, payments
│   └── services/               # 주문·결제 업무 처리
├── frontend/
│   ├── index.html              # 경로별 화면의 공통 HTML 셸
│   └── assets/
│       ├── css/                # 모바일 우선 반응형 스타일
│       ├── js/                 # 순수 JavaScript·fetch·인증 복귀
│       └── images/
├── sql/
│   ├── schema.sql              # 테이블·제약·RLS·원자적 처리 함수
│   ├── seed.sql                # 예제 상품
│   ├── backend-functions.sql   # 동시 장바구니 담기 RPC
│   └── verify.sql              # 개발 DB 검증 후 ROLLBACK
├── tests/                      # 권한·주문·재고·결제 검증
├── .env.example
├── .gitignore
├── requirements.txt
├── render.yaml
├── run.py                      # Python 실행 진입점
├── start.ps1                   # 현재 PC 실행 환경 탐색
└── README.md                   # 실행·배포 안내
```

현재 `docs/`의 설계 문서, `sql/`의 SQL, `app/`의 백엔드, `frontend/`의 반응형 화면, 테스트를 작성했습니다. 실제 프론트엔드는 공통 HTML 셸과 브라우저 JavaScript 모듈 구조이며 [화면·소스 안내](frontend.md)를 참고하세요. 설명 문서는 Markdown으로 작성하며, ERD 원본은 `.mmd` 형식입니다.
