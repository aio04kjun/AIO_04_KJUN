# 4차시. 내 대화 이력을 조회해 말풍선에 연결하기

## 1. 학습목표

[수업 전 안내](../TODAY_GUIDE.md)를 먼저 읽습니다.

내 대화 이력을 조회해 말풍선에 연결하기를 실제 조작으로 확인합니다. 이번 중심 개념은 아래 2번에서 다루며, 차시 끝의 통과 기준은 단계 실습에 있습니다. AI 인터페이스 및 UX 설계에서 사용자 상태와 백엔드 데이터를 일치시키는 능력을 기릅니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

### 내 DB 기록을 화면 목록으로 연결한다

3차시에서는 로그인한 화면을 구분했습니다. 아직 저장된 대화는 보이지 않습니다. 이번에는 `/conversations`로 내 대화 목록을 읽고 첫 번째 ID의 메시지를 조회합니다. 새 메시지 입력은 추가하지 않습니다.

DB 조회 결과를 화면 상태로 옮겨 출력하는 것이 이번 데이터 바인딩입니다. 다음은 네트워크가 없는 설명용 비교입니다.

```python
rows = [{"role": "user", "content": "DB에서 읽은 문장"}]
state = {"messages": []}
print("연결 전:", len(state["messages"]))
state["messages"] = rows
print("연결 후:", state["messages"][0]["content"])
```

예상 출력은 `연결 전: 0`, `연결 후: DB에서 읽은 문장`입니다. 실제 rows는 `api("GET", f"/conversations/{selected_id}/messages")`의 JSON 응답입니다. 같은 결과를 매번 append하면 재실행할 때 중복되므로 목록 자체를 교체합니다.

### 소유권은 화면 필터가 아니라 서버 SQL에서 확인한다

`rooms[0]`은 정렬된 결과의 첫 항목입니다. 목록이 비면 이 접근은 실패하므로 먼저 `if not rooms`에서 안내 후 멈춥니다. 샘플 준비 명령은 기존 계정에 DB 기록을 실제로 넣으며 AI가 만든 답변이 아닙니다.

백엔드는 `require_user`가 확인한 user.id로 `WHERE owner_id = %s`를 적용합니다. 개별 대화 조회도 `id = %s AND owner_id = %s`를 검사합니다. UI에서 타인의 ID를 보내도 서버는 같은 404로 거절합니다. 존재하지 않는 ID와 타인 ID를 구분해서 알려 주지 않는 실습 정책입니다.

말풍선의 `role`은 user/assistant라는 발화자 종류이고, 소유권의 owner_id와 다릅니다. 현재 샘플과 새 저장은 user 발화만 다룹니다. 실제 답변 생성은 하지 않습니다.

### 화면·인증·영구 기록의 수명

| 위치 | 보관하는 것 | 언제 없어지는가 |
| --- | --- | --- |
| Streamlit session_state | 현재 탭의 토큰·사용자·선택·조회 결과 | F5·새 연결·서버 재시작 또는 명시적 초기화 |
| Redis | 토큰 해시 → 검증된 사용자 ID | 로그인 시 정한 TTL 또는 앱 로그아웃 |
| Supabase PostgreSQL | 사용자 소유 대화와 메시지 | 직접 삭제하기 전까지 보존 |

session_state는 서버 메모리에 있으며 브라우저 영구 저장소가 아닙니다. 버튼의 True도 로그인 상태가 아닙니다. 사용자 전용 데이터에 `st.cache_data`나 전역 목록을 사용하지 않습니다. F5 후에는 다시 로그인해서 DB 기록을 읽습니다.

### 기존 백엔드와의 연결 및 달라진 점

백엔드는 2차시부터 준비한 같은 파일입니다. 이번에는 그 안의 DB 조회 경로를 처음 사용합니다.

| 이전 파일·동작 | 새 파일·핵심 구문 | 필요한 이유·관찰 차이 |
| --- | --- | --- |
| 기존 backend06의 list_conversations는 전체 목록 반환 | backend/main.py list_conversations의 WHERE owner_id = %s | B 로그인에서 A의 대화가 목록에 나오지 않음 |
| 기존 backend06의 resolve_conversation은 Redis의 대화방 ID 사용 | require_user로 계정 확인 후 id AND owner_id 조건 | 타인의 ID 직접 요청은 404 |
| Auth 교안은 SQLite notes(owner_id) | 새 kdt_user_chat 대화·메시지 테이블 | 소유자 검사 원칙을 PostgreSQL의 대화 관계에 적용 |

기존 `kdt_hybrid`와 SQLite 파일은 바꾸지 않습니다. 소유자 정보가 없는 기록을 임의로 A/B에게 배정하지 않고 새 스키마에서 시작합니다. 테이블 준비와 기존 자료 호환 한계는 [백엔드 안내](../BACKEND_GUIDE.md)에 있습니다.

### 자료 확인과 반영

검색 키워드: `Streamlit session_state 채팅 history`. 아래 Wikidocs 본문과 코드를 읽고 현재 단계에 맞게 재구성했으며, 기술 동작은 공식 자료와 실제 설치한 SDK로 대조했습니다. 원문 전체 코드나 미확인 버전·인기 지표는 옮기지 않았습니다.

| 읽은 자료 | 참고한 패턴 | 이 차시에 반영한 부분 |
| --- | --- | --- |
| [함께해요 Streamlit: 세션 상태](https://wikidocs.net/352285) | 메시지 목록을 반복해 말풍선에 표시 | messages를 API 조회 결과로 교체. 입력 목록과 DB 원본의 역할 구분 |
| [공식 Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)·[Psycopg 매개변수](https://www.psycopg.org/psycopg3/docs/basic/params.html) | API 역할·실행 순서·한계 대조 | 위 개념 설명과 실제 main.py |

## 3. 코드 제공

### 실행 준비 — Windows CMD

ZIP 내부의 교안은 `lesson04/README.md`, 실행 코드는 `lesson04/main.py`입니다. 전체 실행 코드는 main.py 한 개에 있고 아래에는 중요한 부분만 발췌합니다. `lesson_scope.json`은 품질 검증 명세이며 실행 설정이 아닙니다.

먼저 [백엔드 준비 안내](../BACKEND_GUIDE.md)에 따라 **이번 묶음의 backend/main.py**를 실행합니다. 기존 backend05/backend06/HF 모델 서버에 연결하면 인증·경로 계약이 다릅니다. backend는 2~8차시 내내 같은 한 버전을 사용합니다. DB 초기화·샘플 준비는 수업 전에 한 번 하고, backend 서버와 UI는 별도 CMD에서 동시에 실행합니다.

UI CMD에서 자신의 압축 해제 위치로 이동합니다. 예시는 `C:\AI4\Session_State_02_08`입니다.

```bat
cd /d C:\AI4\Session_State_02_08\lesson04
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
# 선택된 대화의 결과로 교체한다. 이전 대화 목록에 append/extend하지 않는다.
st.session_state["messages"] = []
st.session_state["messages"] = api("GET", f"/conversations/{selected_id}/messages")
```

발췌 앞뒤는 생략했습니다. 이것만 실행 파일로 사용하지 않고 제공된 main.py를 기준으로 아래 단계에서 한 부분씩 수정합니다.

### 작은 단계로 같은 main.py 완성하기

완성본 원본은 ZIP에 남겨 둡니다. 현재 main.py에서 지정 블록만 잠시 덜어 낸 뒤, 같은 파일에 한 부분씩 복원합니다. 다른 차시 파일에서 코드를 가져오지 않습니다. 각 단계의 통과 기준을 확인한 다음 넘어갑니다.

#### 1단계. 로그인 화면부터 확인

- 바꾸는 곳: 현재 main.py에서 [목록]·[첫 대화]·[이력 조회]·[말풍선] 블록을 잠시 뺍니다. 나머지 로그인·로그아웃 준비 코드를 실행합니다.
- 실행: 샘플을 준비한 계정 A 로그인
- 예상 결과·통과 기준: 현재 계정 확인; 아직 말풍선 없음.
- 안 되면 먼저 확인: /me의 인증 성공 여부.

#### 2단계. 내 대화 목록 읽기

- 바꾸는 곳: [목록]과 [첫 대화] 블록을 복원합니다. rooms가 비었으면 멈추는 조건을 먼저 읽습니다.
- 실행: 화면 다시 실행
- 예상 결과·통과 기준: 첫 대화: 학습 메모 표시; 샘플 미준비 계정은 빈 목록 안내.
- 안 되면 먼저 확인: backend seed가 로그인 계정에 대해 실행됐는지.

#### 3단계. 선택된 ID의 메시지 읽기

- 바꾸는 곳: [이력 조회] 블록을 복원합니다. 그 아래 임시로 `st.write("조회 개수:", len(st.session_state["messages"]))`를 넣습니다.
- 실행: 화면 다시 실행
- 예상 결과·통과 기준: 샘플 메시지 수 1 이상; 아직 말풍선 없음.
- 안 되면 먼저 확인: GET 요청 경로의 전체 selected_id.

#### 4단계. 목록을 말풍선에 연결

- 바꾸는 곳: 임시 조회 개수 줄을 빼고 [말풍선] 블록을 복원합니다.
- 실행: 화면 다시 실행을 두 번 누르기
- 예상 결과·통과 기준: 샘플 문장이 보이고 반복 실행해도 중복 안 됨.
- 안 되면 먼저 확인: messages에 append하지 않고 조회 결과를 대입하는지.


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
lesson04/main.py와 backend/main.py를 읽어 줘.
실행은 해당 폴더에서 .env 설정 후 Streamlit과 FastAPI를 각각 실행하는 방식이다.
이번 목표는 내 대화 이력을 조회해 말풍선에 연결하기다.
현재 차시의 단계 입력과 기대 결과를 기준으로 session_state 변경 순서와 실제 API 요청을 추적해 줘.
문제가 있으면 원인 한 가지씩 설명하고 현재 목표에 필요한 최소 변경만 제안해 줘.
로그인 검증·서버 소유권 검사·기존 기록 보존·미확정 저장 ID 재사용 동작은 유지해 줘.
확인할 정상/실패 입력을 제시하고 실행하지 못한 원격 검증은 미검증이라고 밝혀 줘.
.env의 값·비밀번호·토큰·실제 대화 원문은 읽어 출력하거나 전송하지 마.
```

### 복습 과제

메시지 수가 0일 때 `아직 기록이 없습니다`를 표시합니다. 이미 배운 if를 사용하고, 실제 빈 대화가 없다면 설명용 빈 목록으로 분기만 확인한 사실을 구분해 적습니다. 수정 코드, 합성 입력을 사용한 실행 화면 또는 상태 코드, 변경 이유 한 문장을 제출할 증거로 남깁니다. 직접 시도한 뒤 AI에 힌트·원인·검증을 요청합니다. 전체 세션 상태나 실제 인증 토큰을 증거에 포함하지 않습니다. 다음 차시는 과제 완성에 의존하지 않습니다.
