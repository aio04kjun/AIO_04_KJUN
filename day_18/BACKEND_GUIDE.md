# 로그인·사용자 대화 이력 백엔드 안내

## 차시와 백엔드 연결

이 묶음의 `backend/main.py` 한 개를 2~8차시에서 계속 사용합니다. 차시마다 백엔드를 바꾸거나 여러 백엔드를 동시에 켜지 않습니다. UI와 백엔드는 서로 다른 프로세스이며 import로 연결하지 않습니다.

| UI | 사용하는 HTTP 경로 | 이번에 확인하는 역할 |
| --- | --- | --- |
| lesson02/main.py | POST /auth/login, GET /me | 인증 성공 결과 보관과 서버 재확인 |
| lesson03/main.py | 위 경로 + POST /auth/logout | 화면 분기와 앱 세션 종료 |
| lesson04/main.py | 위 경로 + GET /conversations, GET /conversations/{id}/messages | 자기 소유 기록 조회 |
| lesson05/main.py | 같은 조회 경로 | 선택한 전체 UUID로 조회 |
| lesson06/main.py | 위 경로 + POST /conversations/{id}/messages | 실제 저장 후 재조회 |
| lesson07/main.py | 같은 경로 | /me의 TTL과 401·503·연결 실패 구분 |
| lesson08/main.py | 같은 경로 | 계정 전환·소유권·미확정 저장의 통합 확인 |

backend는 요청 범위 전체에서 사용하는 고정 준비 서비스입니다. 초반 차시에는 로그인·사용자 확인 경로만 사용하고, DB 경로는 4차시부터 연결합니다. 모델 호출은 UI와 backend 어느 쪽에도 없습니다. 기록 저장·선택이라는 이번 목표에 집중합니다. 샘플 문장은 준비 명령이 넣는 합성 문장이며 AI 생성 결과가 아닙니다.

## 기존 코드와 달라진 점

확인한 원본은 `supabase_auth_lesson08.zip`의 lesson08/main.py, `streamlit_integrated_lessons05_08.zip`의 streamlit_integrated/backend06/main.py, `HF_Streamlit_Lessons02_04.zip`의 backend04/main.py입니다.

| 비교 | 기존 코드 | 이번 backend/main.py |
| --- | --- | --- |
| 인증 | Auth 교안의 sign_in_with_password·get_user·Depends | 같은 공식 SDK 방식 재사용, 요청마다 새 SDK·HTTPX 객체 |
| 로그인 응답 | access/refresh 쌍과 만료 정보 | access_token·token_type·expires_in·user_id·email. refresh_token 미전달 |
| 로그인 유지 | JWT 검증 또는 대화방 Redis 세션이 각각 별도로 존재 | JWT를 get_user로 검증하고 Redis 앱 허용 목록도 확인 |
| 헤더 | 하이브리드는 X-Session-Id → 대화방 ID | Authorization: Bearer → 검증된 사용자 ID |
| 소유권 | 기존 하이브리드 목록에 owner_id 조건 없음 | 모든 대화 조회·저장에 id와 owner_id 조건 적용 |
| 영구 테이블 | kdt_hybrid.conversations/messages, SQLite notes | kdt_user_chat.conversations/messages |
| 모델 응답 | HF backend04는 /chat/stream의 NDJSON 응답 | 이번 서비스는 모델·스트리밍을 실행하지 않음 |
| 로그아웃 | Auth 교안은 Supabase SDK sign_out 요청 | 해당 토큰의 Redis 앱 등록 삭제. 다른 앱/기기 세션 종료는 요청하지 않음 |

새 단원의 UI를 연결할 때는 기존 8000 서버를 Ctrl+C로 종료하고 이번 backend를 같은 포트로 시작합니다. 기존 DB 테이블·파일은 삭제하지 않습니다. 소유자 없는 옛 기록을 자동으로 특정 계정에 배정하거나 이전 notes를 변환하지 않습니다. 새 스키마에서 시작하므로 이전 데이터가 새 화면에 저절로 나타나지 않습니다.

## 수업 전 준비

같은 Supabase 프로젝트의 정상 로그인 가능한 수업용 계정 A·B를 준비합니다. 이전 인증 실습 계정을 재사용해도 됩니다. 확인 메일이 필요한 프로젝트라면 이메일 확인을 완료합니다. 가입 UI를 이 교안에 새로 구현하지 않습니다. 계정이 없다면 프로젝트 Authentication의 사용자 관리에서 계정을 준비한 뒤 진행합니다. 실제 비밀번호는 브라우저 로그인 폼에만 입력하고 코드·자료·프롬프트에 적지 않습니다.

세 가지 역할을 구분합니다. Supabase **프로젝트 URL·publishable key**는 Auth 요청용이고, **DB URI**는 PostgreSQL 연결용입니다. Redis URI는 별도 임시 저장소 주소입니다. Supabase의 Session pooler와 로그인 세션도 다른 개념입니다.

### backend 폴더·Python·패키지

Windows CMD에서 실행합니다. 경로는 실제 압축 해제 위치에 맞춥니다.

```bat
cd /d C:\AI4\Session_State_02_08\backend
python --version
python -c "import sys; print(sys.executable)"
```

`cd /d`는 드라이브와 폴더 이동, `--version`은 Python 버전, `-c`는 따옴표 안 코드 실행입니다. sys.executable로 실제 환경을 확인합니다. 정상 수업 가상환경을 재사용하거나 현재 backend 폴더에서 새 환경을 만듭니다.

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

`-m venv`는 가상환경 생성, `.venv`는 생성할 폴더, activate는 현재 CMD에서 환경 사용입니다. `-m pip install -r`은 설치 목록 파일을 읽어 현재 Python 환경에 설치합니다. copy는 예시 설정을 실제 .env로 복사합니다. 기존 .env가 있으면 덮어쓰지 않고 편집합니다. 설치 완료 또는 Requirement already satisfied 표시를 확인하고 Python 경로도 다시 확인합니다. UI 환경과 같은 환경을 써도 되지만 각 폴더에서 해당 requirements 설치를 확인합니다.

### .env 값 채우기

```dotenv
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_REPLACE_ME
SUPABASE_DB_URL='postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres'
REDIS_URL=redis://127.0.0.1:6379/0
SESSION_TTL_SECONDS=600
```

| 이름 | 확인할 곳·의미 |
| --- | --- |
| SUPABASE_URL | 프로젝트의 API 접속 정보에서 Project URL. 예시 PROJECT_REF를 실제 값으로 교체 |
| SUPABASE_PUBLISHABLE_KEY | 프로젝트 API Keys의 publishable 키. 사용자 JWT·DB 비밀번호와 다름 |
| SUPABASE_DB_URL | Connect → Session pooler의 URI. 사용자·호스트·포트는 본인 화면 값 사용 |
| REDIS_URL | 기존 로컬 Redis 주소. /0은 논리 DB 0번. 쿼리 옵션은 넣지 않음 |
| SESSION_TTL_SECONDS | 로그인 앱 허용 목록의 수명(초). 정상 실습 600, 만료 확인 시 15 |

표시한 URI와 키는 모두 가짜 값입니다. DB URI의 비밀번호 예약문자는 URI 규칙대로 인코딩합니다. 예를 들어 #은 %23, 공백은 %20이며 .env의 따옴표로 감싸는 것과 별개입니다. 문자열에 #·$·공백이 있으면 따옴표로 감싸며, interpolate=False는 ${...}를 치환하지 않습니다. 비밀번호 원문을 무조건 strip하지 않습니다.

`load_dotenv(".env", override=False, interpolate=False)`는 현재 backend 폴더의 .env를 읽고, os.getenv가 값을 조회합니다. 이미 설정된 환경변수가 파일보다 우선합니다. 필수 값 누락·빈 문자열·공백, 잘못된 TTL은 시작 시 거절하고 값 자체는 출력하지 않습니다. .env가 없다는 것만으로 연결 실패라고 판단하지 않으며 환경변수만으로도 실행할 수 있습니다. 다른 폴더에서 실행하면 그 작업 폴더의 .env를 찾으므로 먼저 cd합니다. 수정 후 서버를 재시작합니다.

ClientOptions의 persist_session=False는 SDK 저장소 기록을 끄고, auto_refresh_token=False는 백그라운드 갱신을 끕니다. 두 옵션 기본값은 True입니다. 세션이 아예 발급되지 않는다는 뜻이 아닙니다. httpx_client는 timeout=10초인 호출자의 객체이며 with 종료에서 닫습니다. 매 요청 새 SDK를 사용해 사용자 인증 상태를 전역으로 공유하지 않습니다.

### Redis 준비 확인

기존 kdt-redis가 있다면 상태를 조회합니다.

```bat
docker ps -a --filter name=kdt-redis
```

`docker ps`는 컨테이너 목록, `-a`는 중지된 항목 포함, `--filter name=...`는 이름 필터입니다. STATUS가 Up이면 실행 중, Exited이면 중지 상태입니다. 조회만 수행합니다.

중지된 기존 컨테이너는 시작합니다.

```bat
docker start kdt-redis
```

start는 기존 컨테이너 시작이고 새 컨테이너 생성이 아닙니다. 목록이 비어 **기존 컨테이너가 없을 때만** 다음 명령으로 만듭니다.

```bat
docker run -d --name kdt-redis -p 127.0.0.1:6379:6379 redis:7.4 redis-server --save "" --appendonly no
```

| 부분 | 의미 |
| --- | --- |
| run -d | 컨테이너 생성·백그라운드 실행 |
| --name kdt-redis | 이후 명령에서 찾을 이름 |
| -p 127.0.0.1:6379:6379 | PC의 로컬 주소 6379를 컨테이너 6379에 연결 |
| redis:7.4 | 사용할 Redis 이미지와 버전 계열 |
| redis-server | 컨테이너 안에서 시작할 서버 |
| --save "" | 빈 문자열을 전달해 RDB 자동 스냅샷을 끔 |
| --appendonly no | AOF 기록을 끔. 이번 임시 세션은 재시작 뒤 복원을 기대하지 않음 |

서버가 응답하는지 확인합니다.

```bat
docker exec kdt-redis redis-cli PING
```

exec는 실행 중인 컨테이너 안의 명령 실행, redis-cli는 Redis 명령 전송 도구, PING은 응답 확인입니다. 예상 응답 PONG은 Redis가 응답한다는 뜻이며 호스트 Python 연결까지 검증한 것은 아닙니다. 컨테이너 목록 확인과 다른 검사입니다.

### DB 테이블·샘플 준비

backend 폴더의 CMD에서 테이블을 만듭니다.

```bat
python main.py init
```

init은 이 main.py의 argparse가 해석하는 직접 만든 명령입니다. `__main__`에서 init_db를 호출하며 CREATE SCHEMA/TABLE을 실행합니다. SQL은 같은 main.py 안에 있고 외부 SQL 파일을 읽지 않습니다. 테이블 준비 완료가 나오면 commit된 상태입니다. Uvicorn import 시에는 테이블을 변경하지 않습니다.

기존 수업 계정의 실제 이메일로 아래 예시를 교체합니다. example.com 주소를 그대로 실행하지 않습니다.

```bat
python main.py seed --email learner-a@example.com
python main.py seed --email learner-b@example.com
```

seed는 샘플 준비 동작, --email은 Auth에 이미 있는 수업 계정을 고르는 인자입니다. 이 값은 DB 접속 자격증명이 아니며 비밀번호를 CLI로 받지 않습니다. parse_args가 command와 email을 해석하고 seed_user가 auth.users에서 계정 ID를 찾은 뒤, 그 소유자의 같은 제목 대화 두 개와 샘플 문장을 저장합니다. 동일 계정·샘플의 ID는 일정해 재실행해도 중복되지 않습니다. 계정 생성·비밀번호 변경·기존 행 삭제는 하지 않습니다.

출력은 해당 계정의 샘플 대화 두 개 준비 완료입니다. 없는 계정이면 먼저 Auth 계정을 준비하라는 안내로 끝납니다. 이 준비는 프로젝트 DB의 auth.users 읽기와 새 스키마 생성·쓰기 권한이 있는 서버 DB 연결을 사용합니다. 해당 URI를 UI에 배포하지 않습니다. 새 스키마는 Data API에 노출하도록 추가하지 않습니다. DB 소유권 검사는 이 FastAPI의 SQL에서 수행하며, 직접 DB 연결에 RLS가 자동 적용된다고 설명하지 않습니다.

## 서버 시작·종료·재시작

backend CMD에서 시작합니다.

```bat
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

`-m uvicorn`은 현재 환경의 ASGI 서버, main:app은 main.py의 app 객체, --host는 PC 로컬 연결 주소, --port는 8000 포트, --workers 1은 한 서버 프로세스입니다. --no-access-log는 접근 로그 출력을 끕니다. 요청 본문·비밀번호·토큰을 별도로 로그에 쓰지 않습니다. Application startup complete가 보인 뒤 `http://127.0.0.1:8000/docs`를 열어 경로 목록을 확인합니다. /docs 열기만으로 Auth·Redis·DB 연결 성공을 확인한 것은 아닙니다.

이 CMD는 계속 켜 두고 별도 CMD에서 해당 lessonNN으로 cd해 UI를 시작합니다. UI는 기본 8501, 백엔드는 8000입니다. 다른 차시 UI로 옮길 때는 기존 UI만 Ctrl+C로 중지합니다. backend를 멈추려면 backend CMD에서 Ctrl+C를 누르고, 설정 변경 후에는 같은 명령으로 재시작합니다. 코드에는 /health 경로가 없습니다.

만료 실습은 backend .env의 TTL을 15로 바꾸고 재시작한 뒤 UI에서 로그아웃·재로그인합니다. 기존 키의 TTL은 설정 변경만으로 바뀌지 않습니다. 15초가 지난 뒤 화면 다시 실행을 누르면 401을 확인합니다. 정상 실습을 재개할 때 600으로 복구하고 다시 로그인합니다. 메시지 조회는 TTL을 연장하지 않습니다.

## API 계약

| 요청 | 입력 | 성공 응답 |
| --- | --- | --- |
| POST /auth/login | JSON email·password | access_token·token_type·expires_in·user_id·email |
| GET /me | Authorization Bearer | id·email·ttl |
| POST /auth/logout | 같은 헤더 | ended·user_id |
| GET /conversations | 같은 헤더 | id·title·created_at의 목록 |
| GET /conversations/{id}/messages | 같은 헤더와 전체 대화 UUID | id·role·content·created_at의 목록 |
| POST /conversations/{id}/messages | 같은 헤더, JSON content·request_id | message·replayed |

마지막 두 경로의 {id}는 실제 UUID로 바꿉니다. content는 앞뒤 공백 제거 후 1~1000자, request_id는 UUID입니다. POST 성공은 신규·재전송 모두 200이며 replayed로 구분합니다. owner_id와 role은 입력으로 받지 않습니다. user 역할은 서버에서 정합니다. 개인 경로는 Redis 앱 등록과 Supabase get_user 확인을 모두 요구합니다. Redis 키 이름의 SHA-256은 토큰 원문 노출을 줄이는 용도이며 JWT 서명 검증·비밀번호 해싱을 직접 구현한 것이 아닙니다.

401은 인증 없음·만료·무효, 타인/없는 대화는 404, 같은 요청 ID의 다른 내용은 409, 입력 형식 오류는 422입니다. Auth의 이메일 확인 미완료는 403, 인증 요청 제한은 429, 통신·DB·Redis 장애는 이 실습에서 503입니다. 503을 로그인 만료로 취급하지 않습니다.

## Swagger로 권한 확인

1. 로컬 /docs의 POST /auth/login에서 수업 계정 A로 실행합니다. 성공 응답의 access_token 전체를 로컬에서만 복사해 Authorize의 bearer 값에 넣습니다. HTTPBearer 입력은 토큰만 넣으면 Bearer 접두어를 붙입니다. 캡처·공유·프롬프트에는 토큰을 포함하지 않습니다.
2. GET /me, GET /conversations, 첫 ID의 GET /conversations/{id}/messages를 Execute로 호출합니다. A의 ID를 기록할 때는 실제 사용자 정보 대신 A/B 표기를 씁니다. 데이터 확인은 ID가 전체 값인지 확인합니다.
3. POST /conversations/{id}/messages에서 합성 content와 새 UUID request_id를 넣습니다. UUID는 backend CMD가 아닌 별도 정상 환경 CMD에서 `python -c "from uuid import uuid4; print(uuid4())"`로 생성합니다. -c는 한 줄 코드 실행, uuid4는 새 요청 식별자 생성입니다. 출력 전체를 request_id로 복사합니다.
4. 같은 ID·같은 content로 다시 Execute하면 replayed=True와 같은 message.id여야 합니다. content만 바꾸면 409이고 GET 원본은 그대로여야 합니다.
5. B로 로그인해 Authorize 값을 B 토큰으로 교체하고 A의 대화 ID를 직접 GET·POST합니다. 둘 다 404여야 합니다. Authorize를 해제한 개인 API 요청은 401이어야 합니다.
6. A의 원래 토큰으로 POST /auth/logout을 수행하고 같은 토큰의 GET /me가 401인지 확인합니다. 이미 만료된 토큰의 로그아웃도 401일 수 있습니다. 로컬 토큰 값을 지웁니다.

새로고침 뒤 자동 복원·refresh token 회전·다른 기기 전역 로그아웃은 구현하지 않습니다. Auth SDK 검증과 DB 소유권은 실제 요청마다 수행하지만, 로그인한 화면의 session_state 유지가 이 기능들을 대신하지 않습니다.

## 검증 범위

배포 코드의 Auth·Redis·PostgreSQL 호출은 실제 서비스용입니다. 제작 환경에서는 실제 FastAPI 라우트와 Streamlit AppTest를 연결하고 Auth·Redis·DB를 명시적 대역으로 바꿔 정상/401/404/409/422/503·응답 유실·재조회·계정 전환을 확인했습니다. DB 대역은 PostgreSQL SQL 실행 성공의 증거가 아니며 SQLite 결과를 PostgreSQL 검증이라고 기록하지 않습니다. 실제 원격 Auth·DB·실 Redis 서버와 Windows 브라우저 조작은 위 절차로 확인해야 합니다.

참고: [Supabase 로그인](https://supabase.com/docs/reference/python/auth-signinwithpassword), [사용자 확인](https://supabase.com/docs/reference/python/auth-getuser), [ClientOptions](https://supabase.com/docs/reference/python/initializing), [Psycopg 값 바인딩](https://www.psycopg.org/psycopg3/docs/basic/params.html), [Redis TTL](https://redis.io/docs/latest/commands/ttl/).
