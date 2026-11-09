# 모델·백엔드 연결과 실행

## 어떤 서버를 켜야 하나요?

모델 서버는 8080, FastAPI는 8000, 화면 서버는 8501 포트를 사용합니다. FastAPI의 backend 파일들은 서로 import하지 않습니다. **아래 표의 해당 서버 한 개만** 8000에 실행합니다. 서버를 바꿀 때 이전 CMD에서 Ctrl+C로 종료한 뒤 새 폴더에서 실행합니다.

| 차시 | 화면 폴더 | FastAPI 폴더 | 이전 서버와 달라진 점 |
| --- | --- | --- | --- |
| 2 | lesson02 | 없음 | 화면이 모델 API를 직접 호출 |
| 3 | lesson03 | backend03 | 화면이 history를 보내고 서버가 모델 호출 |
| 4 | lesson04 | backend04 | 기존 Auth 로그인 재사용, Redis에서 사용자·대화별 이력 읽기 |
| 5 | lesson05 | backend05 | 4차시 서버를 기준으로 모델 입력 함수 한 곳 수정 |
| 6 | lesson06 | backend06 | 영구 대화 목록·질문/답변 저장과 재조회 추가 |
| 7 | lesson07 | backend06 | 서버 그대로 사용, 화면에서 실패 보관·재시도 추가 |
| 8 | lesson08 | backend08 | 대화별 goal 저장 항목과 목표 반영 함수 추가 |

4차시 이후에는 화면이 전체 이력을 다시 보내지 않습니다. 서버가 인증한 사용자와 선택한 대화를 기준으로 기록을 읽습니다. 5차시에서 고친 내용은 backend06에 이미 적용되어 있으므로 과제 완료 여부와 무관하게 시작할 수 있습니다.

## 공통 모델 서버

1차시에서 사용한 서버를 계속 사용할 수 있습니다. 새로 시작해야 한다면 별도 CMD에서 실행합니다.

```bat
llama serve -hf ggml-org/Qwen3.5-0.8B-GGUF:Q8_0 --alias local-chat --host 127.0.0.1 --port 8080 --reasoning-budget 0
```

local-chat은 .env의 LLM_MODEL과 맞추는 모델 별명입니다. 처음 모델을 받는 시간은 수업 전에 확보합니다. 이미 서버가 정상 실행 중이면 다시 시작하지 않습니다. 준비 확인은 별도 CMD에서 실행합니다.

```bat
curl http://127.0.0.1:8080/v1/models
```

목록에 local-chat이 보이는지 확인합니다. llama 명령이 없는 환경은 1차시 설치 준비를 사용합니다. 실행 파일 이름이 llama-server인 환경에서는 `llama serve` 대신 `llama-server`로 같은 옵션을 실행합니다.

공통 모델 설정은 다음과 같습니다. 로컬 서버에 인증 키를 지정하지 않은 구성의 예시이며, 다른 모델 API를 쓰면 해당 서비스의 주소·모델·키로 바꿉니다.

```dotenv
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL=local-chat
LLM_API_KEY=local-not-used
```

## 3차시 서버

Windows CMD에서 실행합니다. 화면 CMD는 별도로 엽니다.

```bat
cd /d C:\AI4\MultiTurn_02_08\backend03
python -m pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

기존 .env가 있으면 복사 대신 값을 확인합니다. `main:app`은 현재 폴더 main.py의 FastAPI 객체 app을 실행한다는 뜻입니다. http://127.0.0.1:8000/docs 에 POST /chat이 보이면 화면을 실행합니다.

## 4~5차시 인증과 Redis 준비

기존 Supabase Auth 실습에서 로그인 가능한 A·B 계정을 사용합니다. 확인 메일을 요구하는 프로젝트는 계정의 이메일 확인을 마칩니다. UI에 가입 기능은 없으므로 필요하면 Supabase Authentication에서 수업용 계정을 먼저 준비합니다.

기존 Redis 컨테이너가 있다면 시작하고 연결을 확인합니다.

```bat
docker start kdt-redis
docker exec kdt-redis redis-cli PING
```

PONG이면 연결된 것입니다. 컨테이너가 처음인 경우에만 아래 명령으로 만듭니다. 이 설정은 Redis 임시 데이터를 영구 저장하지 않습니다.

```bat
docker run -d --name kdt-redis -p 127.0.0.1:6379:6379 redis:7.4 redis-server --save "" --appendonly no
```

backend04 또는 backend05 폴더에서 requirements 설치와 .env 복사를 마친 뒤 다음 값을 채웁니다. 모델 설정 세 항목도 같은 .env에 둡니다.

```dotenv
SUPABASE_URL=https://PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_REPLACE_ME
REDIS_URL=redis://127.0.0.1:6379/0
SESSION_TTL_SECONDS=1800
```

프로젝트 URL과 publishable key는 Supabase 프로젝트의 API Keys 화면에서 확인합니다. 로그인 토큰은 화면 폼에서 로그인하면 받으므로 .env에 적지 않습니다. 로그인 등록은 최대 1800초이며 원래 토큰 수명이 더 짧으면 그 수명을 따릅니다. Redis 대화는 마지막 저장 후 3600초 동안 최근 50턴을 보관합니다. 다시 로그인할 때 대화 목록까지 복원하는 기능은 6차시부터 사용합니다.

메모장에서 예시 값을 실제 수업 프로젝트 값으로 바꾸고 저장한 뒤 다음 명령을 이어갑니다. 기존 .env가 있으면 copy를 생략합니다.

4차시 실행 예시입니다. 5차시는 경로의 backend04를 backend05로 바꿉니다.

```bat
cd /d C:\AI4\MultiTurn_02_08\backend04
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## 6~7차시 DB 준비와 서버

backend06은 기존 계정·인증·Redis 로그인 방식을 유지하면서, Supabase PostgreSQL에 대화를 저장합니다. **kdt_multiturn** 스키마를 새로 사용합니다. 이전 kdt_user_chat·kdt_hybrid 테이블을 변경하거나 옛 기록을 자동 이관하지 않습니다. 4~5차시의 Redis 대화도 자동 복사하지 않습니다.

Supabase의 Connect에서 PostgreSQL **Session pooler** 연결 URI를 확인해 backend06/.env에 추가합니다. Auth용 publishable key는 DB 비밀번호가 아닙니다. 비밀번호의 URI 특수문자는 인코딩된 값을 사용합니다. 화면 폴더에는 DB URI를 넣지 않습니다.

```dotenv
SUPABASE_DB_URL='postgresql://postgres.PROJECT_REF:ENCODED_PASSWORD@POOLER_HOST:5432/postgres'
```

backend06 폴더에서 설치·.env 입력을 마친 뒤 실행합니다.

```bat
cd /d C:\AI4\MultiTurn_02_08\backend06
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
python main.py init
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

init은 main.py 안의 SQL로 스키마와 테이블을 준비합니다. 기존 데이터는 삭제하지 않습니다. `멀티턴 테이블 준비 완료`를 확인한 뒤 서버를 실행합니다. 대화는 로그인한 화면에서 직접 만드므로 별도 seed 명령은 없습니다. 7차시는 이 서버를 유지합니다.

| 테이블 | 보관 내용 | 화면과 연결 |
| --- | --- | --- |
| kdt_multiturn.conversations | 대화 ID·소유자·제목 | 로그인 계정의 대화 목록 |
| kdt_multiturn.turns | 요청 번호·질문·답변·그때 모델 입력 | 말풍선 복원과 같은 요청 재확인 |

질문과 답변을 한 행에 저장하므로 성공한 턴 단위로 복원합니다. 모델 오류가 나면 그 턴을 저장하지 않습니다. DB 연결은 서버가 맡고 모든 대화 읽기·저장 전에 소유자를 확인합니다.

## 8차시 서버 교체

backend06을 Ctrl+C로 종료합니다. backend08/.env에는 같은 프로젝트·Redis·DB URI·모델 설정을 입력합니다. 다음 명령으로 목표 항목을 준비하고 서버를 실행합니다.

```bat
cd /d C:\AI4\MultiTurn_02_08\backend08
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
python main.py init
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

8차시 init은 conversations 테이블에 goal 항목을 추가합니다. 기존 행의 목표는 빈 문자열이며 기존 질문·답변은 남습니다. 새 목표는 새 대화 만들기에서 입력합니다. 시작 함수는 목표를 반영하지 않는 상태이므로 8차시 교안에서 한 곳을 수정합니다.

## 요청이 전달되는 경로

| 화면에서 하는 일 | HTTP 요청 | 서버가 받는 값 |
| --- | --- | --- |
| 3차시 질문 전송 | POST /chat | ChatInput의 question·history |
| 4차시 이후 로그인 | POST /auth/login | email·password |
| 로그인 상태 확인 | GET /me | 헤더의 토큰을 require_user가 확인 |
| 로그아웃 | POST /auth/logout | 해당 토큰의 Redis 로그인 등록 삭제 |
| 4~5차시 이력 읽기 | GET /conversations/{id}/messages | 사용자 ID와 대화 ID로 Redis 조회 |
| 6차시 이후 목록·생성 | GET·POST /conversations | 검증된 소유자·대화 제목, 8차시는 goal 추가 |
| 6차시 이후 이력 읽기 | GET /conversations/{id}/messages | 소유권 확인 후 DB 질문·답변 읽기 |
| 4차시 이후 질문 전송 | POST /chat | conversation_id·question, 6차시부터 request_id 추가 |

화면에서 보낸 Authorization 헤더는 HTTPBearer가 scheme과 credentials로 나눕니다. require_user는 토큰을 Supabase Auth로 확인한 뒤 user 딕셔너리를 반환합니다. FastAPI가 이 결과를 각 경로 함수의 user 매개변수에 넣습니다. 사용자 ID를 UI가 임의로 선택하는 방식이 아닙니다.

참고: [llama.cpp 서버](https://github.com/ggml-org/llama.cpp/tree/master/tools/server), [Supabase 사용자 확인](https://supabase.com/docs/reference/python/auth-getuser), [Psycopg 트랜잭션](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
