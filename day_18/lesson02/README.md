# 2차시. 로그인 결과를 session_state에 보관하기

## 1. 학습목표

[수업 전 안내](../TODAY_GUIDE.md)를 먼저 읽습니다.

로그인 결과를 session_state에 보관하기를 실제 조작으로 확인합니다. 이번 중심 개념은 아래 2번에서 다루며, 차시 끝의 통과 기준은 단계 실습에 있습니다. AI 인터페이스 및 UX 설계에서 사용자 상태와 백엔드 데이터를 일치시키는 능력을 기릅니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

### 인증 성공은 버튼 값이 아니라 서버 응답으로 판단한다

1차시에서는 입력 목록을 기억했습니다. 이제 기억할 것은 로그인 버튼이 아니라 **인증에 성공한 응답**입니다. 버튼 클릭은 이번 실행에서만 True입니다. 토큰은 서버에 사용자 인증을 증명하는 문자열이며 화면에 출력하지 않습니다.

이메일·비밀번호 입력을 `st.form`으로 묶으면 제출할 때 두 값을 함께 받습니다. `clear_on_submit=True`는 제출 후 입력칸을 기본값으로 비웁니다. 기본값 False이면 입력을 유지합니다. `type="password"`는 화면의 글자만 가립니다. 실제 전송 보호는 HTTPS가 담당하며, 여기의 HTTP 주소는 같은 PC의 로컬 백엔드 전용입니다.

설명용 비교는 인증 서비스를 흉내 내는 합성 데이터입니다. 실제 로그인 검증은 이 코드가 아니라 SDK가 합니다. 아래 코드는 일반 Python에서 실행할 수 있습니다.

```python
clicked = [True, False]
state = {}
for submitted in clicked:
    temporary_login = submitted
    if submitted:
        state["user"] = {"id": "demo-A"}
    print(temporary_login, state.get("user", {}).get("id"))
```

예상 출력은 `True demo-A`, `False demo-A`입니다. 두 번째 실행에서는 버튼 결과가 False여도 저장한 사용자 정보는 남습니다. main.py의 `submitted`는 clicked의 한 값, `access_token`과 `user`는 유지할 인증 결과에 대응합니다. 이 단순 예제의 user 값을 직접 정하는 방식으로 실제 인증을 구현하지 않습니다.

### 한 번의 로그인 요청이 지나가는 곳

브라우저 폼 제출 → Streamlit의 `api("POST", "/auth/login", ...)` → FastAPI `login` → Supabase `sign_in_with_password` → 성공 토큰의 해시와 user ID를 Redis에 TTL로 등록 → 필요한 응답만 UI에 반환 → session_state에 보관합니다.

그 뒤 `/me`를 호출하면 Redis 등록 여부와 Supabase `get_user(token)` 검증을 모두 거칩니다. 토큰을 디코딩해서 id만 읽고 믿지 않습니다. API helper는 HTTPX로 요청하고 `raise_for_status()`로 4xx/5xx를 구분하며 실패 시 `st.stop()`으로 뒤 실행을 막습니다. timeout 15초는 통신 단계별 제한이며 전체 작업 시간 제한이 아닙니다.

이 차시는 폼을 계속 보여 주므로 로그인한 뒤에도 폼을 볼 수 있습니다. 다음 차시에서 로그인 여부에 따라 화면을 나눕니다.

### 화면·인증·영구 기록의 수명

| 위치 | 보관하는 것 | 언제 없어지는가 |
| --- | --- | --- |
| Streamlit session_state | 현재 탭의 토큰·사용자·선택·조회 결과 | F5·새 연결·서버 재시작 또는 명시적 초기화 |
| Redis | 토큰 해시 → 검증된 사용자 ID | 로그인 시 정한 TTL 또는 앱 로그아웃 |
| Supabase PostgreSQL | 사용자 소유 대화와 메시지 | 직접 삭제하기 전까지 보존 |

session_state는 서버 메모리에 있으며 브라우저 영구 저장소가 아닙니다. 버튼의 True도 로그인 상태가 아닙니다. 사용자 전용 데이터에 `st.cache_data`나 전역 목록을 사용하지 않습니다. F5 후에는 다시 로그인해서 DB 기록을 읽습니다.

### 기존 백엔드와의 연결 및 달라진 점

실제 확인한 이전 자료는 `supabase_auth_lesson08.zip/lesson08/main.py`와 `streamlit_integrated_lessons05_08.zip/streamlit_integrated/backend06/main.py`입니다.

| 이전 동작 | 이번 backend/main.py 변경 | 이유·같은 입력의 차이 |
| --- | --- | --- |
| Auth 교안의 /auth/login은 access/refresh 쌍을 반환 | login은 access_token·user_id·email·expires_in만 반환하고 Redis 등록 | 이번 UI는 자동 갱신 대신 재로그인. 새 로그인 없이는 Redis 등록이 없어 기존 토큰만 재사용 불가 |
| Auth 교안의 get_current_user는 get_user로 검증 | require_user가 Redis 등록도 먼저 확인 | JWT가 아직 유효해도 앱 세션 만료 뒤 /me는 401 |
| 기존 하이브리드는 X-Session-Id가 대화방을 가리킴 | Authorization Bearer JWT와 사용자 ID 등록 사용 | 대화방 세션을 사용자 로그인으로 오인하지 않음 |
| Auth 교안 로그아웃은 SDK sign_out | 이 앱의 Redis 등록 제거 | 이 백엔드 접근을 즉시 막고 다른 기기 전체 로그아웃은 하지 않음 |

모델 서버의 /chat/stream은 이번 UI가 호출하지 않습니다. 이 단원의 목표는 인증 상태와 이력 바인딩이므로 스트리밍 코드를 복사하지 않습니다. [BACKEND_GUIDE](../BACKEND_GUIDE.md)에 새 계약과 준비 순서가 있습니다.

### 자료 확인과 반영

검색 키워드: `Streamlit 로그인 st.form session_state`. 아래 Wikidocs 본문과 코드를 읽고 현재 단계에 맞게 재구성했으며, 기술 동작은 공식 자료와 실제 설치한 SDK로 대조했습니다. 원문 전체 코드나 미확인 버전·인기 지표는 옮기지 않았습니다.

| 읽은 자료 | 참고한 패턴 | 이 차시에 반영한 부분 |
| --- | --- | --- |
| [함께해요 Streamlit: 폼](https://wikidocs.net/352287) | 폼 제출 결과를 한 번 처리하는 패턴 | 로그인 폼과 submitted 분기. 비밀번호를 출력하지 않고 실제 API로 전달하도록 변경 |
| [공식 form 1.51](https://docs.streamlit.io/1.51.0/develop/api-reference/execution-flow/st.form)·[Supabase 로그인](https://supabase.com/docs/reference/python/auth-signinwithpassword) | API 역할·실행 순서·한계 대조 | 위 개념 설명과 실제 main.py |

## 3. 코드 제공

### 실행 준비 — Windows CMD

ZIP 내부의 교안은 `lesson02/README.md`, 실행 코드는 `lesson02/main.py`입니다. 전체 실행 코드는 main.py 한 개에 있고 아래에는 중요한 부분만 발췌합니다. `lesson_scope.json`은 품질 검증 명세이며 실행 설정이 아닙니다.

먼저 [백엔드 준비 안내](../BACKEND_GUIDE.md)에 따라 **이번 묶음의 backend/main.py**를 실행합니다. 기존 backend05/backend06/HF 모델 서버에 연결하면 인증·경로 계약이 다릅니다. backend는 2~8차시 내내 같은 한 버전을 사용합니다. DB 초기화·샘플 준비는 수업 전에 한 번 하고, backend 서버와 UI는 별도 CMD에서 동시에 실행합니다.

UI CMD에서 자신의 압축 해제 위치로 이동합니다. 예시는 `C:\AI4\Session_State_02_08`입니다.

```bat
cd /d C:\AI4\Session_State_02_08\lesson02
python --version
python -c "import sys; print(sys.executable)"
```

`cd /d`는 드라이브와 폴더를 바꾸고, `--version`은 실제 실행 버전, `-c`는 따옴표 안의 Python 코드 실행입니다. sys.executable이 정상 수업 환경을 가리키는지 확인합니다. Python 3.12에서 검증했습니다. `.venv` 표시만으로 판단하지 않습니다.

기존 정상 수업 가상환경을 그대로 써도 됩니다. 새 환경이 필요하면 현재 차시 폴더에서 아래 생성·활성화를 수행합니다.

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

`-m venv`는 환경 생성 모듈, `.venv`는 만들 폴더, activate는 현재 CMD에서 그 환경 사용입니다. `-m pip install -r`은 현재 Python의 pip가 requirements.txt 목록을 설치하게 합니다. copy는 예시 설정을 실제 .env로 복사합니다. 기존 .env가 있으면 덮어쓰지 말고 편집기로 현재 값을 확인합니다. 설치 뒤 앞의 Python 경로 확인을 반복합니다. requirements는 직접 의존성만 고정하며 전체 잠금 파일은 아닙니다.

UI의 .env에는 다음 한 항목만 둡니다.

```dotenv
API_BASE_URL=http://127.0.0.1:8000
```

`load_dotenv(".env", override=False, interpolate=False)`는 **현재 작업 폴더** 파일을 환경변수에 올리고 os.getenv가 값을 읽습니다. override=False는 이미 설정된 환경변수를 우선하고 interpolate=False는 `${...}` 치환을 막습니다. .env가 없어도 환경변수가 있으면 실행됩니다. 누락·공백·주소 형식 오류는 값 자체를 표시하지 않고 중단합니다. DB URI·Supabase 키는 UI 설정에 넣지 않고 backend의 .env에만 둡니다. .gitignore는 실제 .env·가상환경·캐시를 제외합니다.

UI를 실행합니다.

```bat
python -m streamlit run main.py
```

`-m streamlit`은 현재 Python의 Streamlit, run은 웹 앱 실행, main.py는 대상입니다. CMD에 Local URL이 나오면 준비된 상태입니다. 기본 `http://localhost:8501` 대신 실제 표시된 주소를 엽니다. 화면 입력은 브라우저에서 합니다. 서버 명령은 CMD에 입력합니다. 이전 차시 Streamlit이 실행 중이면 그 CMD에서 Ctrl+C로 종료하고 현재 차시에서 다시 실행합니다. backend는 계속 켜 둡니다.

### 핵심 로직 — main.py에서 같은 구문 찾기

```python
result = api("POST", "/auth/login", {"email": email.strip(), "password": password})
        clear_private()  # 새 인증 결과를 넣기 전에 이전 사용자 상태부터 지운다.
        st.session_state["access_token"] = result["access_token"]
```

발췌 앞뒤는 생략했습니다. 이것만 실행 파일로 사용하지 않고 제공된 main.py를 기준으로 아래 단계에서 한 부분씩 수정합니다.

### 작은 단계로 같은 main.py 완성하기

완성본 원본은 ZIP에 남겨 둡니다. 현재 main.py에서 지정 블록만 잠시 덜어 낸 뒤, 같은 파일에 한 부분씩 복원합니다. 다른 차시 파일에서 코드를 가져오지 않습니다. 각 단계의 통과 기준을 확인한 다음 넘어갑니다.

#### 1단계. 폼 입력을 묶기

- 바꾸는 곳: 완성본을 ZIP에 남겨 둡니다. 현재 main.py의 [로그인] 블록 안 submitted 처리에서 인증 요청·상태 대입을 잠시 빼고 `st.info("입력 준비 완료")`만 둡니다. 아래 사용자 확인 if 블록도 잠시 뺍니다. api·환경설정·초기화 함수는 준비 코드로 유지합니다.
- 실행: 이메일·비밀번호 입력 후 로그인 누르기
- 예상 결과·통과 기준: 입력 준비 완료 안내만 보이고 비밀번호가 출력되지 않음.
- 안 되면 먼저 확인: st.form 들여쓰기와 submit 버튼이 폼 안에 있는지.

#### 2단계. 실제 인증 요청 보내기

- 바꾸는 곳: submitted의 else 안에 완성본의 `result = api("POST", "/auth/login", ...)` 한 요청을 복원하고 아래에는 `st.success("인증 요청 성공")`만 둡니다. 아직 access_token을 상태에 대입하지 않습니다.
- 실행: 준비한 수업 계정으로 로그인
- 예상 결과·통과 기준: 실제 백엔드·Auth가 성공했을 때만 성공 안내.
- 안 되면 먼저 확인: backend CMD와 SUPABASE_URL·키 이름 설정 확인.

#### 3단계. 인증 결과 보관·재사용

- 바꾸는 곳: 성공 안내를 빼고 완성본의 clear_private와 access_token·user 대입 세 줄을 복원합니다. 끝의 `if st.session_state["access_token"]:` 사용자 확인 블록을 복원합니다.
- 실행: 로그인 후 화면 다시 실행을 두 번 누르기
- 예상 결과·통과 기준: 로그인 유지 중과 같은 계정 표시; 비밀번호 재입력 없이 /me 통과.
- 안 되면 먼저 확인: 토큰 대입 위치가 submitted 성공 안인지.

#### 4단계. 실패를 성공으로 표시하지 않기

- 바꾸는 곳: 코드 추가 없이 잘못된 비밀번호와 서버 중단을 나누어 확인합니다. 로그인 실패 후에는 화면 다시 실행을 누릅니다.
- 실행: 잘못된 비밀번호로 로그인; 서버를 잠시 끄고 로그인
- 예상 결과·통과 기준: 실패 시 토큰을 새로 저장하지 않고 오류 표시.
- 안 되면 먼저 확인: 오류 상태 코드와 네트워크 오류를 혼동하지 않는지.


### 중단·오류에서 다시 시작하기

UI를 멈출 때는 해당 CMD에서 Ctrl+C를 누릅니다. 다시 시작할 때는 현재 차시 폴더에서 같은 Streamlit 실행 명령을 사용하고 재로그인합니다. F5 후 자동 로그인 복원은 구현하지 않았습니다. 서버를 다시 켜는 명령은 [백엔드 안내](../BACKEND_GUIDE.md)에 있습니다.

| 현상 | 먼저 확인 | 복구 후 확인 |
| --- | --- | --- |
| 모듈을 못 찾음 | 실제 Python 경로·현재 가상환경 | requirements 재설치 후 실행 |
| 로그인 안 됨 | 준비한 Auth 계정·이메일 확인 여부 | 401/403/429/503을 구분하고 안내에 맞게 처리 |
| 주소가 맞는데 연결 실패 | backend CMD가 켜져 있는지 | /docs 접속 후 UI 재실행 |
| 이력이 없음 | seed한 이메일과 로그인 계정이 같은지 | 해당 계정 샘플 준비 뒤 다시 조회 |
| 매번 로그인이 풀림 | 무조건 초기화·F5 여부 | 조건부 초기화로 복구, 같은 세션의 버튼으로 확인 |
| 선택 때 위젯 상태 오류 | selected_id 대입 위치 | selectbox를 만들기 전 대입 |

옛 Python/Conda 경로를 찾지 못하면 먼저 `deactivate`로 기존 환경을 해제하고 `where python`으로 후보 경로를 조회한 뒤 `python --version`으로 외부 Python이 실제 동작하는지 확인합니다. WindowsApps 경로만으로 실패를 단정하지 않습니다. 외부 Python이 정상일 때만 고장 난 환경 폴더를 `ren .venv .venv_backup`으로 이름 변경해 보관하고 위의 생성·활성화·경로 확인·설치 순서로 복구합니다. ren은 삭제가 아닌 이름 변경이며, 같은 백업 이름이 있으면 .venv_backup2처럼 다른 이름을 씁니다. 부모 폴더 환경을 쓰고 있었다면 그 환경 위치에서 백업합니다. 외부 Python도 실패하면 그 설치부터 해결합니다.

### 확인한 범위와 직접 확인할 범위

Python 3.12·Streamlit 1.51.0의 AppTest와 실제 FastAPI 라우트를 HTTP 테스트 클라이언트로 연결해 정상·실패·중간 단계 흐름을 확인했습니다. 테스트에서는 Auth·Redis·DB의 응답을 명시적 대역으로 제공했습니다. 실제 Supabase 프로젝트 자격증명이 없어 원격 인증·PostgreSQL 저장과 실 Redis 서버의 연결 성공은 확인하지 않았습니다. 배포 코드는 실제 서비스만 호출하며 대역/SQLite 모드가 없습니다. 실제 환경은 위 실행 절차와 BACKEND_GUIDE의 검증 순서로 확인합니다. Windows CMD·브라우저 F5·새 탭 조작도 직접 확인 항목입니다.

## 4. Vibe 코딩에 유용한 프롬프트

```text
lesson02/main.py와 backend/main.py를 읽어 줘.
실행은 해당 폴더에서 .env 설정 후 Streamlit과 FastAPI를 각각 실행하는 방식이다.
이번 목표는 로그인 결과를 session_state에 보관하기다.
현재 차시의 단계 입력과 기대 결과를 기준으로 session_state 변경 순서와 실제 API 요청을 추적해 줘.
문제가 있으면 원인 한 가지씩 설명하고 현재 목표에 필요한 최소 변경만 제안해 줘.
로그인 검증·서버 소유권 검사·기존 기록 보존·미확정 저장 ID 재사용 동작은 유지해 줘.
확인할 정상/실패 입력을 제시하고 실행하지 못한 원격 검증은 미검증이라고 밝혀 줘.
.env의 값·비밀번호·토큰·실제 대화 원문은 읽어 출력하거나 전송하지 마.
```

### 복습 과제

로그인 성공 화면에 이메일 앞에 `환영합니다:`를 붙이고, 비밀번호 재입력 없이 다시 실행해도 표시가 유지되는지 확인합니다. 비밀번호·토큰 출력은 추가하지 않습니다. 수정 코드, 합성 입력을 사용한 실행 화면 또는 상태 코드, 변경 이유 한 문장을 제출할 증거로 남깁니다. 직접 시도한 뒤 AI에 힌트·원인·검증을 요청합니다. 전체 세션 상태나 실제 인증 토큰을 증거에 포함하지 않습니다. 다음 차시는 과제 완성에 의존하지 않습니다.
