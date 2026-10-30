# ORBIT 쇼핑몰 — Step 3

Python · FastAPI · Uvicorn · Supabase Auth/PostgreSQL과 순수 HTML/CSS/JavaScript로 구현한 반응형 쇼핑몰입니다. 우주·Liquid Design 방향을 반영했습니다.

## 바로 실행하기

현재 작업 PC의 PowerShell에서 다음 명령을 실행하고 [http://localhost:8000](http://localhost:8000)을 엽니다.

```powershell
cd C:\AIO_04_kjun\shopping-mall
.\start.ps1 -Demo
```

체험 계정은 `demo@orbit.local` / `Orbit1234!`입니다. Supabase 키 없이 화면과 구매 흐름을 확인하며, 실제 결제는 없고 재시작하면 데이터가 초기화됩니다. [설치·실제 Supabase 연결·단계별 구매 확인](docs/run-guide.md)에 실행 방법을 정리했습니다.

## 먼저 읽을 문서

- [API 엔드포인트 명세](docs/api-spec.md)
- [화면·프론트엔드 안내](docs/frontend.md)
- [백엔드 구조·인증 흐름](docs/backend.md)
- [SQL 적용 안내](docs/sql-application.md)
- [ERD](docs/erd.md) · [테이블 정의](docs/table-definition.md) · [구매 시뮬레이션](docs/purchase-simulation.md)
- [Render 배포 안내](docs/deployment.md)
- [현재 Supabase 연결 상태](docs/supabase-connection.md)

## 1. Supabase 설정

신규 개발 프로젝트의 SQL Editor에서 다음 순서로 실행합니다.

1. [schema.sql](sql/schema.sql)
2. [seed.sql](sql/seed.sql)
3. [backend-functions.sql](sql/backend-functions.sql)

이전 Step 1의 수정된 6개 테이블 스키마를 이미 설치했다면 3번만 추가 실행합니다. 수정 전 5개 테이블 구조가 설치되어 있다면 별도 마이그레이션이 필요합니다. schema.sql은 기존 테이블을 삭제하지 않으며 재설치용이 아닙니다.

Supabase 프로젝트의 Auth에서 이메일·비밀번호 가입을 사용합니다. 이메일 인증을 켜면 메일 인증 이후 로그인할 수 있습니다. 이메일 인증을 끈 개발 환경에서는 회원가입 응답에서 signed_in=true와 인증 쿠키를 받습니다.

## 2. 로컬 실행 — PowerShell

아래 명령은 `shopping-mall` 폴더에서 실행합니다. Python 3.12 이상을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에서 프로젝트 URL과 두 API 키를 입력합니다. 실제 비밀키는 Git에 추가하지 않습니다.

| 환경변수 | 용도 |
|---|---|
| SUPABASE_URL | 프로젝트 URL |
| SUPABASE_PUBLISHABLE_KEY | 공개 앱 키. 기존 프로젝트는 anon JWT 키도 사용 가능 |
| SUPABASE_SECRET_KEY | 서버 전용 키. 기존 프로젝트는 service_role JWT 키도 사용 가능 |
| APP_ORIGIN | 로컬은 http://localhost:8000, 끝에 경로 없음 |
| COOKIE_SECURE | 로컬 HTTP는 false, 배포 HTTPS는 true |
| ENABLE_MOCK_PAYMENTS | true일 때만 모의 결제 허용. 실제 금액은 청구되지 않음 |

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file .env --no-proxy-headers
```

- API 문서: [Swagger UI](http://localhost:8000/docs)
- 상태 확인: [health](http://localhost:8000/health)
- `/`는 쇼핑몰 메인 화면입니다. HTML과 API는 동일한 FastAPI 서버에서 제공합니다.

localhost와 127.0.0.1은 서로 다른 출처입니다. 브라우저에서 APP_ORIGIN과 동일한 주소를 사용하세요.

## 3. API 호출 예제 — PowerShell

모든 변경 요청은 JSON 본문과 X-CSRF-Token 헤더, 발급된 쿠키가 필요합니다.

```powershell
$shopBase = 'http://localhost:8000'
$shopCsrf = Invoke-RestMethod "$shopBase/api/v1/auth/csrf" -SessionVariable shopSession
$shopHeaders = @{ 'X-CSRF-Token' = $shopCsrf.data.csrf_token }
$shopLogin = @{
    email = 'test@example.com'
    password = 'your-test-password'
    next = '/cart'
} | ConvertTo-Json
Invoke-RestMethod "$shopBase/api/v1/auth/login" -Method Post -WebSession $shopSession -Headers $shopHeaders -ContentType 'application/json' -Body $shopLogin
Invoke-RestMethod "$shopBase/api/v1/users/me" -WebSession $shopSession
```

Swagger에서도 먼저 GET `/api/v1/auth/csrf`를 실행하고 응답의 csrf_token을 변경 요청의 X-CSRF-Token 입력칸에 복사합니다. 같은 브라우저가 인증 쿠키를 자동으로 전송합니다. 본문이 없는 작업도 `{}`를 전송합니다.

## 4. 테스트

일반 Python 표준 unittest를 사용하며 JavaScript 실행 환경은 필요하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

백엔드 테스트 41개와 HTML·로컬 체험 통합 테스트 12개, 총 53개가 통과했습니다. 외부 Supabase에 실제 계정이나 주문을 생성하지 않습니다. 체험 환경의 실제 브라우저에서도 비회원 로그인 복귀부터 모의 구매·구매 내역까지 확인했습니다.

실제 DB 검증은 개발용 프로젝트에서 테스트 계정 2개 이상을 준비하고 [verify.sql](sql/verify.sql)을 실행합니다. 성공 시 PASS를 출력하고 모든 테스트 데이터 변경을 ROLLBACK합니다. 동시 세션 경합과 실제 인증 메일은 별도로 확인해야 합니다.

## 현재 구현 범위

회원가입·로그인·로그아웃·세션 갱신, 회원 프로필 조회·수정·탈퇴, 상품 조회, 장바구니, 주문 생성·내역·상세·미결제 취소, 모의 결제와 각 기능의 반응형 화면을 구현했습니다. 보호 화면의 로그인 리다이렉트와 next 보존도 연결했습니다.

이메일·비밀번호 변경과 비밀번호 재설정은 이번 프로필 수정 범위에 포함하지 않습니다. 프로필 수정 대상은 이름·연락처입니다. 실제 PG 결제·환불은 구현 범위에 포함하지 않습니다.

Supabase PostgreSQL에 스키마·상품을 설치하고 롤백 기반 구매 검증을 통과했습니다. .env의 API 키로 Auth·Data API 및 실제 서버의 상품 조회를 확인하고 실연결 모드로 전환했습니다. 인증 메일·실제 사용자 로그인 전체 흐름·동시 세션 경합·Render 배포는 아직 검증하지 않았습니다.
