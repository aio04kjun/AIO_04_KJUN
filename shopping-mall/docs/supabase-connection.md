# Supabase 연결 상태

[실행 방법](run-guide.md) · [SQL 안내](sql-application.md)

**Supabase 실연결을 완료했습니다.** 공개 Data API·Auth API·서버 비밀키의 접근 권한을 읽기 전용으로 확인했습니다. 서버의 demo_mode=false, 상품 5개 조회도 확인했습니다. 결제는 기존대로 모의 결제입니다.

접속 주소는 [http://localhost:8000](http://localhost:8000)입니다. 실제 계정을 새로 생성하거나 인증 메일을 발송하지는 않았습니다. 체험용 demo@orbit.local 계정은 실연결 환경의 실제 계정이 아닙니다.

## 완료한 작업

- 사용자가 지정한 `day_11/config.json`을 사용했습니다. 같은 폴더의 `config.local.json`이 있으면 로컬 값을 우선 적용합니다. 원본 설정 파일은 변경하지 않았습니다.
- 해당 Supabase PostgreSQL에 암호화된 DB 연결을 확인했습니다.
- 쇼핑몰 테이블이 없는 것을 확인한 뒤 schema.sql·seed.sql·backend-functions.sql을 한 트랜잭션으로 설치했습니다. 기존의 다른 테이블은 변경하지 않았습니다.
- 회원·상품·장바구니·주문·주문 항목·결제의 6개 테이블과 업무 함수 4개를 설치했습니다. 가입 프로필 생성용 트리거 함수도 포함됩니다.
- 예제 상품 5개를 등록했습니다.
- 실제 DB에서 주문 재요청·가격 스냅샷·결제 실패 후 재시도·중복 재고 차감 방지·재고 부족·RLS·미결제 취소·장바구니 유지를 검증했습니다.
- 검증에 사용한 임시 인증 계정과 모든 테스트 데이터 변경은 롤백했습니다. 실제 DB의 동시 세션 경합 시험은 별도입니다.

## API 키 설정과 조회 방법

### API 키를 찾는 위치

1. [Supabase 대시보드](https://supabase.com/dashboard)에 로그인합니다.
2. config.json에서 사용하는 것과 같은 프로젝트를 선택합니다.
3. 왼쪽 **Project Settings(설정) → API Keys**로 이동합니다.
4. **Publishable and secret API keys** 탭에서 아래 값을 복사합니다. 키가 아직 없다면 해당 화면에서 생성합니다.

| 대시보드 항목 | 키의 시작 형태 | .env 변수 |
|---|---|---|
| Publishable key | sb_publishable_… | SUPABASE_PUBLISHABLE_KEY |
| Secret key | sb_secret_… | SUPABASE_SECRET_KEY |

기존 프로젝트의 Legacy API Keys 탭만 사용한다면 anon은 공개 키 변수, service_role은 서버 비밀키 변수에 대응합니다. JWT Signing Keys의 키나 DB 비밀번호를 복사하는 것이 아닙니다.

공식 안내: [Supabase API 키](https://supabase.com/docs/guides/getting-started/api-keys), [새 API 키 조회·전환](https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys).

config.json의 host·port·dbname·user·password는 **PostgreSQL 직접 접속용**입니다. 현재 웹 앱이 사용하는 Supabase Auth와 Data API의 API 키는 포함되어 있지 않습니다. DB 비밀번호를 API 키 대신 사용할 수 없습니다.

[shopping-mall/.env](../.env)의 프로젝트 URL과 API 키 두 개를 설정하고 연결을 확인했습니다. 다른 환경을 설정할 때는 해당 프로젝트의 API Keys에서 아래 값을 복사합니다.

```dotenv
SUPABASE_PUBLISHABLE_KEY=프로젝트의_Publishable_키
SUPABASE_SECRET_KEY=프로젝트의_Secret_키
```

기존 키를 쓰는 프로젝트라면 각각 anon 키와 service_role 키를 사용합니다. 실제 비밀키는 채팅이나 Markdown 문서에 기록하지 말고 Git에서 제외된 .env에만 저장하세요.

`start.ps1`을 **-Demo 없이** 실행합니다. 이전 체험 서버를 종료하고 8000 포트의 실연결 서버로 교체했습니다. 이전 화면이 열려 있다면 브라우저를 새로고침합니다. 이전 체험 쿠키 등 유효하지 않은 사용자 토큰은 재로그인으로 안내합니다.

웹 로그인·가입에는 실제 Supabase 계정을 사용합니다. 프로젝트에서 이메일 인증을 켰다면 가입 후 인증 메일을 확인해야 합니다. 테스트 과정에서는 새 회원이나 주문을 만들지 않았습니다.

API 연결을 다시 확인하는 읽기 전용 스크립트도 준비했습니다. 키·토큰·회원 데이터는 출력하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts/check_api_connection.py
```

## 설정 파일을 이용한 DB 재확인

관리 작업에는 requirements-db.txt의 psycopg가 필요합니다. 프로젝트 폴더에서 다음 명령으로 DB 상태만 읽을 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-db.txt
.\.venv\Scripts\python.exe scripts/setup_supabase.py
```

`--apply`는 쇼핑몰 테이블이 전혀 없을 때만 신규 설치합니다. 이미 완전한 테이블·함수가 있으면 보존하며, 일부만 있는 상태는 자동 변경하지 않습니다. `--verify`는 검증 데이터를 항상 롤백하는 개발용 검사입니다. 스크립트는 비밀번호·API 키를 출력하지 않습니다.

API·실행 모드 확인과 자동 테스트 53개가 통과했습니다. 실제 사용자의 회원가입·이메일 인증·로그인 전체 흐름, 실제 동시 세션 경합 및 Render 배포는 아직 검증하지 않았습니다.
