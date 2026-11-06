# 5차시. 제목이 같은 대화도 ID로 구분해 선택하기

## 1. 학습목표

[수업 전 안내](../TODAY_GUIDE.md)를 먼저 읽습니다.

제목이 같은 대화도 ID로 구분해 선택하기를 실제 조작으로 확인합니다. 이번 중심 개념은 아래 2번에서 다루며, 차시 끝의 통과 기준은 단계 실습에 있습니다. AI 인터페이스 및 UX 설계에서 사용자 상태와 백엔드 데이터를 일치시키는 능력을 기릅니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

### 화면에 보이는 제목과 서버에 보낼 ID를 나눈다

4차시는 첫 대화만 보여 주었습니다. 두 대화의 제목이 같으면 제목을 키로 쓰는 딕셔너리에서 한 대화가 덮어써집니다. 사람이 볼 제목은 그대로 두고 프로그램이 사용하는 값은 고유 ID로 정합니다.

```python
rooms = [{"id": "A", "title": "학습 메모"}, {"id": "B", "title": "학습 메모"}]
by_title = {}
by_id = {}
for room in rooms:
    by_title[room["title"]] = room["id"]
    by_id[room["id"]] = room["title"]
print("제목을 키로:", len(by_title))
print("ID를 키로:", len(by_id), list(by_id))
```

예상 출력은 `제목을 키로: 1`, `ID를 키로: 2 ['A', 'B']`입니다. 실제 main.py의 labels는 by_id에 해당합니다. 제목 뒤의 ID 일부는 사람이 구분할 표시일 뿐이고 API에는 전체 UUID를 보냅니다.

`st.selectbox`의 options는 `ids`, 반환값은 선택한 ID입니다. `format_func=room_label`은 표시만 바꿉니다. 함수 이름을 넘기면 Streamlit이 옵션을 표시할 때 실제 함수를 호출합니다. `key="selected_id"`는 선택 위젯과 session_state의 연결 이름입니다.

위젯을 만든 후 같은 키를 대입하지 않습니다. 목록에 이전 선택이 없을 때만 **위젯 생성 전** 유효한 첫 ID로 맞춥니다. 선택을 바꾸면 다시 실행되고 새 ID로 메시지를 재조회해 기존 목록을 교체합니다. 이전 대화에 새 대화 내용을 붙이지 않습니다.

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

검색 키워드: `Streamlit selectbox key format_func`. 아래 Wikidocs 본문과 코드를 읽고 현재 단계에 맞게 재구성했으며, 기술 동작은 공식 자료와 실제 설치한 SDK로 대조했습니다. 원문 전체 코드나 미확인 버전·인기 지표는 옮기지 않았습니다.

| 읽은 자료 | 참고한 패턴 | 이 차시에 반영한 부분 |
| --- | --- | --- |
| [함께해요 Streamlit: 선택형 입력](https://wikidocs.net/352270) | selectbox의 options와 표시 문자열 | 제목 중복을 허용하고 ID를 반환값으로 유지. 표시 함수만 적용 |
| [공식 selectbox 1.51](https://docs.streamlit.io/1.51.0/develop/api-reference/widgets/st.selectbox) | API 역할·실행 순서·한계 대조 | 위 개념 설명과 실제 main.py |

## 3. 코드 제공

### 실행 준비 — Windows CMD

ZIP 내부의 교안은 `lesson05/README.md`, 실행 코드는 `lesson05/main.py`입니다. 전체 실행 코드는 main.py 한 개에 있고 아래에는 중요한 부분만 발췌합니다. `lesson_scope.json`은 품질 검증 명세이며 실행 설정이 아닙니다.

먼저 [백엔드 준비 안내](../BACKEND_GUIDE.md)에 따라 **이번 묶음의 backend/main.py**를 실행합니다. 기존 backend05/backend06/HF 모델 서버에 연결하면 인증·경로 계약이 다릅니다. backend는 2~8차시 내내 같은 한 버전을 사용합니다. DB 초기화·샘플 준비는 수업 전에 한 번 하고, backend 서버와 UI는 별도 CMD에서 동시에 실행합니다.

UI CMD에서 자신의 압축 해제 위치로 이동합니다. 예시는 `C:\AI4\Session_State_02_08`입니다.

```bat
cd /d C:\AI4\Session_State_02_08\lesson05
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
selected_id = st.selectbox(
    "대화 선택", ids,  # 선택 후보는 ID들이다. index 기본값은 0이다.
    format_func=room_label,  # 표시만 제목+ID 일부로 바꾼다. 기본은 값의 문자열 표시다.
    key="selected_id",  # 선택값과 session_state를 연결하는 이름이다.
)
```

발췌 앞뒤는 생략했습니다. 이것만 실행 파일로 사용하지 않고 제공된 main.py를 기준으로 아래 단계에서 한 부분씩 수정합니다.

### 작은 단계로 같은 main.py 완성하기

완성본 원본은 ZIP에 남겨 둡니다. 현재 main.py에서 지정 블록만 잠시 덜어 낸 뒤, 같은 파일에 한 부분씩 복원합니다. 다른 차시 파일에서 코드를 가져오지 않습니다. 각 단계의 통과 기준을 확인한 다음 넘어갑니다.

#### 1단계. 첫 대화만 보던 위치 확인

- 바꾸는 곳: 현재 main.py의 [선택] 블록만 잠시 빼고 그 위치에 `selected_id = rooms[0]["id"]`를 둡니다. 나머지 로그인·조회·말풍선은 유지합니다.
- 실행: 계정 A 로그인
- 예상 결과·통과 기준: 첫 대화만 표시.
- 안 되면 먼저 확인: seed로 대화 두 개가 있는지.

#### 2단계. ID로 선택하기

- 바꾸는 곳: 임시 첫 ID 줄을 빼고 [선택] 블록을 복원합니다. 처음에는 selectbox의 `format_func=room_label` 인자만 잠시 뺍니다.
- 실행: UUID 옵션 두 개를 차례로 선택
- 예상 결과·통과 기준: 선택에 따라 샘플 1/2가 바뀜.
- 안 되면 먼저 확인: options가 제목 목록이 아니라 ids인지.

#### 3단계. 표시 제목을 읽기 쉽게 바꾸기

- 바꾸는 곳: selectbox에 `format_func=room_label`을 다시 넣습니다. room_label은 이미 준비한 labels에서 제목과 ID 일부를 읽습니다.
- 실행: 학습 메모 두 항목을 번갈아 선택
- 예상 결과·통과 기준: 제목이 같아도 ID 일부로 구별되고 API에는 전체 ID 전송.
- 안 되면 먼저 확인: 표시 함수가 ID가 아닌 title을 반환값으로 바꾸고 있지 않은지.

#### 4단계. 재실행 때 선택 유지

- 바꾸는 곳: 코드는 유지하고 두 번째 항목에서 화면 다시 실행을 누릅니다.
- 실행: 두 번째 항목 선택 → 다시 실행 두 번
- 예상 결과·통과 기준: 같은 selected_id와 해당 말풍선 유지.
- 안 되면 먼저 확인: 선택 키를 매 실행 첫 ID로 덮어쓰지 않는지.


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
lesson05/main.py와 backend/main.py를 읽어 줘.
실행은 해당 폴더에서 .env 설정 후 Streamlit과 FastAPI를 각각 실행하는 방식이다.
이번 목표는 제목이 같은 대화도 ID로 구분해 선택하기다.
현재 차시의 단계 입력과 기대 결과를 기준으로 session_state 변경 순서와 실제 API 요청을 추적해 줘.
문제가 있으면 원인 한 가지씩 설명하고 현재 목표에 필요한 최소 변경만 제안해 줘.
로그인 검증·서버 소유권 검사·기존 기록 보존·미확정 저장 ID 재사용 동작은 유지해 줘.
확인할 정상/실패 입력을 제시하고 실행하지 못한 원격 검증은 미검증이라고 밝혀 줘.
.env의 값·비밀번호·토큰·실제 대화 원문은 읽어 출력하거나 전송하지 마.
```

### 복습 과제

표시 라벨을 `제목 (ID 앞 6글자)`로 바꿉니다. 두 대화의 반환값은 여전히 전체 UUID이고 각각 다른 기록이 보이는지 확인합니다. 수정 코드, 합성 입력을 사용한 실행 화면 또는 상태 코드, 변경 이유 한 문장을 제출할 증거로 남깁니다. 직접 시도한 뒤 AI에 힌트·원인·검증을 요청합니다. 전체 세션 상태나 실제 인증 토큰을 증거에 포함하지 않습니다. 다음 차시는 과제 완성에 의존하지 않습니다.
