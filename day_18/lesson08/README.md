# 8차시. 두 계정으로 로그인·이력·전환 검증하기

## 1. 학습목표

[수업 전 안내](../TODAY_GUIDE.md)를 먼저 읽습니다.

두 계정으로 로그인·이력·전환 검증하기를 실제 조작으로 확인합니다. 이번 중심 개념은 아래 2번에서 다루며, 차시 끝의 통과 기준은 단계 실습에 있습니다. AI 인터페이스 및 UX 설계에서 사용자 상태와 백엔드 데이터를 일치시키는 능력을 기릅니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

### 계정 전환에서 한 묶음으로 지울 상태

7차시는 실패 유형을 구분했습니다. 마지막에는 로그인·선택·조회·미확정 저장이 **같은 사용자에 속하는지** 전체 흐름을 검증합니다. 새 알고리즘을 여럿 더하지 않고 사용자 경계 한 가지를 확인합니다.

```python
state = {"bound_user_id": "A", "selected_id": "A방", "messages": ["A문장"], "pending": "A입력"}
verified_id = "B"
print("정리 전:", state["messages"])
if state["bound_user_id"] != verified_id:
    for key in ("selected_id", "messages", "pending"):
        state.pop(key, None)
    state["bound_user_id"] = verified_id
print("정리 후:", state.get("messages", []), state["bound_user_id"])
```

예상 출력은 `정리 전: ['A문장']`, `정리 후: [] B`입니다. verified_id는 실제 앱에서는 `/me`가 검증해 반환한 ID입니다. `bound_user_id`는 마지막 화면 자료가 어느 사용자에 묶였는지 나타내는 표시이며 인증 자체는 아닙니다.

main.py의 `[사용자 경계]` 블록은 profile을 확인한 뒤, selectbox를 만들기 전에 실행됩니다. 사용자가 바뀌었으면 선택 키·메시지·pending을 제거하고 새 사용자의 목록을 읽습니다. 정상 로그인과 로그아웃도 clear_private로 정리하므로 이 블록은 잘못 남은 상태에 대한 추가 확인입니다. 서버의 소유권 검사를 대신하지 않습니다.

`계정 바꾸기`는 현재 앱 세션 종료와 로컬 정리를 마친 뒤 새 로그인 폼으로 이동합니다. DB 행은 남습니다. 같은 탭에서 A→B→A로 전환하면 B에게 A 기록이 안 보이고, 다시 A로 들어왔을 때 A의 저장 기록이 복원되어야 합니다.

이 로그인·선택·이력의 일관성 검증은 이후 RAG·에이전트의 사용자별 메모리를 화면에 표시할 때 재사용합니다. 이번 코드에는 RAG·LangGraph·모델 호출을 미리 넣지 않습니다.

### 화면·인증·영구 기록의 수명

| 위치 | 보관하는 것 | 언제 없어지는가 |
| --- | --- | --- |
| Streamlit session_state | 현재 탭의 토큰·사용자·선택·조회 결과 | F5·새 연결·서버 재시작 또는 명시적 초기화 |
| Redis | 토큰 해시 → 검증된 사용자 ID | 로그인 시 정한 TTL 또는 앱 로그아웃 |
| Supabase PostgreSQL | 사용자 소유 대화와 메시지 | 직접 삭제하기 전까지 보존 |

session_state는 서버 메모리에 있으며 브라우저 영구 저장소가 아닙니다. 버튼의 True도 로그인 상태가 아닙니다. 사용자 전용 데이터에 `st.cache_data`나 전역 목록을 사용하지 않습니다. F5 후에는 다시 로그인해서 DB 기록을 읽습니다.

### 기존 백엔드와의 연결

실행 흐름은 Streamlit → 같은 backend/main.py → Supabase Auth·Redis 확인 → 필요한 PostgreSQL 처리입니다. 2차시에서 마련한 백엔드는 교체하지 않습니다. 이번 main.py가 사용하는 경로와 역할은 [연결 표](../BACKEND_GUIDE.md#차시와-백엔드-연결)에 있습니다. UI와 서버 파일을 서로 import하지 않고 HTTP로 연결합니다.

### 자료 확인과 반영

검색 키워드: `Streamlit session_state 사용자 전환 selectbox`. 아래 Wikidocs 본문과 코드를 읽고 현재 단계에 맞게 재구성했으며, 기술 동작은 공식 자료와 실제 설치한 SDK로 대조했습니다. 원문 전체 코드나 미확인 버전·인기 지표는 옮기지 않았습니다.

| 읽은 자료 | 참고한 패턴 | 이 차시에 반영한 부분 |
| --- | --- | --- |
| [함께해요 Streamlit: 세션 상태](https://wikidocs.net/352285)·[선택형 입력](https://wikidocs.net/352270) | 상태 초기화·위젯 키와 선택 관계 | 검증된 계정이 바뀌면 selectbox 생성 전에 선택·이력·pending을 정리 |
| [공식 위젯 수명](https://docs.streamlit.io/develop/concepts/architecture/widget-behavior)·[Supabase get_user](https://supabase.com/docs/reference/python/auth-getuser) | API 역할·실행 순서·한계 대조 | 위 개념 설명과 실제 main.py |

## 3. 코드 제공

### 실행 준비 — Windows CMD

ZIP 내부의 교안은 `lesson08/README.md`, 실행 코드는 `lesson08/main.py`입니다. 전체 실행 코드는 main.py 한 개에 있고 아래에는 중요한 부분만 발췌합니다. `lesson_scope.json`은 품질 검증 명세이며 실행 설정이 아닙니다.

먼저 [백엔드 준비 안내](../BACKEND_GUIDE.md)에 따라 **이번 묶음의 backend/main.py**를 실행합니다. 기존 backend05/backend06/HF 모델 서버에 연결하면 인증·경로 계약이 다릅니다. backend는 2~8차시 내내 같은 한 버전을 사용합니다. DB 초기화·샘플 준비는 수업 전에 한 번 하고, backend 서버와 UI는 별도 CMD에서 동시에 실행합니다.

UI CMD에서 자신의 압축 해제 위치로 이동합니다. 예시는 `C:\AI4\Session_State_02_08`입니다.

```bat
cd /d C:\AI4\Session_State_02_08\lesson08
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
# 기록을 묶은 사용자와 방금 검증한 사용자가 다르면 화면 상태를 먼저 초기화한다.
if st.session_state.get("bound_user_id") != profile["id"]:
    for key in ("conversations", "selected_id", "messages", "pending"):
        st.session_state.pop(key, None)
    st.session_state["bound_user_id"] = profile["id"]
```

발췌 앞뒤는 생략했습니다. 이것만 실행 파일로 사용하지 않고 제공된 main.py를 기준으로 아래 단계에서 한 부분씩 수정합니다.

### 작은 단계로 같은 main.py 완성하기

완성본 원본은 ZIP에 남겨 둡니다. 현재 main.py에서 지정 블록만 잠시 덜어 낸 뒤, 같은 파일에 한 부분씩 복원합니다. 다른 차시 파일에서 코드를 가져오지 않습니다. 각 단계의 통과 기준을 확인한 다음 넘어갑니다.

#### 1단계. 검증 기준선 만들기

- 바꾸는 곳: 현재 main.py에서 [사용자 경계] 블록과 계정 바꾸기 버튼 두 줄만 잠시 뺍니다. 기존 로그아웃은 유지합니다.
- 실행: 계정 A 로그인 → 문장 A-확인 저장
- 예상 결과·통과 기준: A의 저장 기록만 보임.
- 안 되면 먼저 확인: seed와 저장을 A 계정으로 수행했는지.

#### 2단계. 화면 자료의 사용자 경계 표시

- 바꾸는 곳: [사용자 경계] 블록을 profile 확인 뒤·목록 조회 전에 복원합니다. 조건이 선택 위젯을 만들기 전에 실행되는지 확인합니다.
- 실행: 로그아웃 → B 로그인
- 예상 결과·통과 기준: bound_user_id는 B, 선택·이력·pending은 B 기준으로 시작.
- 안 되면 먼저 확인: owner 표시가 profile의 검증 ID인지.

#### 3단계. 한 동작으로 계정 바꾸기

- 바꾸는 곳: 계정 바꾸기 버튼과 logout_and_clear 호출을 원래 위치에 복원합니다.
- 실행: B에서 계정 바꾸기 → A 로그인
- 예상 결과·통과 기준: B의 임시 상태가 사라지고 A의 DB 기록 복원.
- 안 되면 먼저 확인: 토큰만 교체하고 선택·pending을 남기지 않는지.

#### 4단계. 타인 ID와 부분 실패까지 검증

- 바꾸는 곳: 아래 통합 확인 표를 수행합니다. API의 권한 실패 검사는 로컬 Swagger에서 실제 토큰을 화면/공유 문서에 남기지 않고 수행합니다.
- 실행: A·B 조회/전환, 타인 대화 ID GET/POST, 만료·서버중단
- 예상 결과·통과 기준: 타인 ID는 404, 미인증은 401, 중복 요청은 한 행.
- 안 되면 먼저 확인: UI 표시뿐 아니라 서버 응답과 DB 행 수도 확인하는지.


### 통합 확인 표

| 조작 | 기대 결과 | 남길 근거 |
| --- | --- | --- |
| A 로그인·첫 대화 저장·재조회 | A-확인 한 행, 같은 계정 유지 | 화면과 같은 대화의 GET 결과 |
| 같은 request_id·같은 content로 재전송 | replayed=True, 동일 message.id | 응답과 행 수 |
| 같은 request_id·다른 content | 409, 기존 내용 유지 | 상태 코드·다시 조회 |
| A 로그아웃 후 B 로그인 | A 문장·선택·pending이 B에게 안 보임 | 두 계정의 목록과 화면 |
| B 토큰으로 A 대화 GET·POST | 둘 다 404, DB 변화 없음 | 두 상태 코드 |
| 헤더 없이 개인 API 요청 | 401 | 상태 코드 |
| TTL 만료 뒤 다시 실행 | 로그인 안내, DB 기록 보존 | 재로그인 후 재조회 |
| DB 저장 뒤 응답 전달 실패 | pending 유지, 같은 ID 확인 시 한 행 | 재확인 응답·행 수 |
| 서버 중단 상태에서 로그아웃 | 로컬 정리, 서버 종료 미확인 안내 | 안내 문구 |
| F5 후 A 재로그인 | 빈 UI 상태에서 A DB 기록 복원 | 새 로그인과 재조회 |

직접 API 검사는 [백엔드 안내의 Swagger 확인 절차](../BACKEND_GUIDE.md#swagger로-권한-확인)를 사용합니다. 토큰을 보고서·스크린샷·AI 프롬프트에 포함하지 않습니다. 실제 원격 서비스에서 확인하지 않은 칸은 미확인으로 남깁니다.

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
lesson08/main.py와 backend/main.py를 읽어 줘.
실행은 해당 폴더에서 .env 설정 후 Streamlit과 FastAPI를 각각 실행하는 방식이다.
이번 목표는 두 계정으로 로그인·이력·전환 검증하기다.
현재 차시의 단계 입력과 기대 결과를 기준으로 session_state 변경 순서와 실제 API 요청을 추적해 줘.
문제가 있으면 원인 한 가지씩 설명하고 현재 목표에 필요한 최소 변경만 제안해 줘.
로그인 검증·서버 소유권 검사·기존 기록 보존·미확정 저장 ID 재사용 동작은 유지해 줘.
확인할 정상/실패 입력을 제시하고 실행하지 못한 원격 검증은 미검증이라고 밝혀 줘.
.env의 값·비밀번호·토큰·실제 대화 원문은 읽어 출력하거나 전송하지 마.
```

### 복습 과제

통합 확인 표에서 정상·만료·계정 전환 중 한 항목씩 골라 재검증합니다. 실제 계정 정보 대신 A/B 표기를 쓰고, 어느 상태가 남고 지워졌는지 한 문장씩 정리합니다. 수정 코드, 합성 입력을 사용한 실행 화면 또는 상태 코드, 변경 이유 한 문장을 제출할 증거로 남깁니다. 직접 시도한 뒤 AI에 힌트·원인·검증을 요청합니다. 전체 세션 상태나 실제 인증 토큰을 증거에 포함하지 않습니다. 다음 차시는 과제 완성에 의존하지 않습니다.
