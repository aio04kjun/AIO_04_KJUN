# 4차시. 계정과 대화별로 컨텍스트 나누기

## 1. 학습목표

[수업 전 안내](../TODAY_GUIDE.md)를 먼저 확인합니다.

- 검증된 계정과 대화 ID로 기록을 나눕니다.
- 새 대화를 시작할 때 새로운 ID를 만듭니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

A가 말한 이름이 B의 대화에 섞이면 안 됩니다. 화면이 보낸 이름을 믿는 대신, 서버가 로그인 토큰으로 확인한 사용자 ID를 기록의 주소에 넣습니다.

화면은 요청 헤더에 `Authorization: Bearer 토큰`을 보냅니다. FastAPI의 `Depends(bearer)`가 이 헤더를 읽고 require_user의 credentials에 넣습니다. 예를 들어 가짜 헤더가 `Bearer demo-token`이면 `credentials.scheme`은 `Bearer`, `credentials.credentials`는 `demo-token`입니다. `Annotated`는 값의 타입과 이 전달 지시를 함께 적는 문법입니다. `| None`은 값이 없을 수도 있다는 표시이고, 실제 누락 처리는 `HTTPBearer(auto_error=False)`와 require_user가 맡습니다.

토큰을 꺼냈다고 로그인 검증이 끝난 것은 아닙니다. 기존 Supabase `get_user(token)`으로 사용자를 확인하고, Redis에 등록된 앱 세션도 확인합니다. `/chat`의 user는 FastAPI가 `Depends(require_user)`의 반환값으로 넣습니다. 로그인 ID를 요청 본문에 따로 적지 않습니다.

Redis 기록 키는 `[확인된 사용자 ID] + [대화 ID]`로 나뉩니다. 화면의 새 대화 버튼도 대화 ID를 바꿔야 새 기록을 읽습니다. `str(uuid4())`는 새 대화를 구별할 임의의 번호를 만듭니다.

기록은 마지막 저장 후 1시간 유지하며 최근 50턴까지 보관합니다. 화면의 대화 ID는 해당 브라우저 연결에 보관됩니다. 다시 로그인하면 새 대화가 시작되며, 지난 기록 목록을 복원하는 기능은 6차시에서 연결합니다.

### 수정 전 위치와 이번에 바꿀 함수

`new_conversation()`은 `st.session_state["messages"] = []`만 실행합니다. 서버에서 읽을 대화 ID를 바꾸지 않아 같은 기록을 다시 가져옵니다.

수정할 파일은 **lesson04/main.py**입니다. 아래 함수로 교체합니다. 전체 실행 코드는 [main.py](main.py)에 있으며, 여기는 수정할 부분만 표시합니다.

```python
def new_conversation():
    st.session_state["conversation_id"] = str(uuid4())
    st.session_state["messages"] = []
```

참고: [FastAPI 의존성](https://fastapi.tiangolo.com/tutorial/dependencies/), [Supabase 사용자 확인](https://supabase.com/docs/reference/python/auth-getuser).

## 3. 코드 제공

### 준비와 실행

Windows CMD에서 현재 차시 폴더로 이동합니다. 기존 수업 가상환경을 사용하거나 처음 한 번만 생성·활성화합니다. [서버 실행 안내](../BACKEND_GUIDE.md)에서 이번 차시에 해당하는 서버를 먼저 준비합니다.

```bat
cd /d C:\AI4\MultiTurn_02_08\lesson04
python -m pip install -r requirements.txt
copy .env.example .env
python -m streamlit run main.py --server.address 127.0.0.1 --server.port 8501
```

패키지를 설치하고 설정 예시를 복사한 뒤 화면 서버를 실행합니다. **기존 .env가 있으면 복사로 덮어쓰지 말고 값을 확인**합니다. 파일 미리보기가 아니라 브라우저의 http://127.0.0.1:8501 에서 실습합니다. 종료는 이 CMD에서 Ctrl+C입니다.

화면 폴더의 .env에는 `API_BASE_URL=http://127.0.0.1:8000`을 사용합니다. 모델 키와 DB 접속 값은 백엔드 폴더의 .env에만 둡니다. 이번 차시는 **backend04**와 연결합니다.

### 실행해 보고 한 곳 바꾸기

1. A 계정으로 로그인하고 `내 이름은 민수고 좋아하는 과일은 귤이야.`를 전송합니다. 대화 ID 앞부분을 메모합니다.
2. **새 대화**를 누릅니다. 시작 코드에서는 ID가 그대로이고 앞선 말풍선도 다시 나타납니다. 문제는 토큰이 아니라 대화 ID를 그대로 쓴 데 있습니다.
3. lesson04/main.py의 `new_conversation()`을 위 코드로 교체합니다. **새 대화**를 누르면 ID가 바뀌고 말풍선이 비어야 합니다.
4. **계정 바꾸기 / 로그아웃**으로 B 계정에 로그인합니다. `내 이름이 뭐야?`를 묻고 직전 모델 입력을 펼칩니다. A가 보낸 민수·귤 문장이 포함되지 않아야 합니다. 이름을 모른다는 정확한 답변 표현은 달라도 됩니다.
5. B가 자신의 이름을 알려준 뒤 다시 물어 B의 최근 이력이 전달되는지 확인합니다. 다른 사람의 실제 정보 대신 위 합성 문장을 사용합니다.

정확한 AI 문장은 달라질 수 있습니다. 먼저 펼친 모델 입력과 말풍선 개수를 확인한 뒤 답변이 앞선 내용을 참고했는지 읽습니다.

<details>
<summary>실행이 멈추거나 화면이 비어 있을 때</summary>

- 다운로드한 파일의 미리보기 대신 CMD에 표시된 Streamlit 주소를 엽니다.
- 제목도 보이지 않으면 브라우저에서 Ctrl+Shift+R을 누르고 실행 CMD의 오류를 확인합니다. [공통 문제 해결](../TROUBLESHOOTING.md)을 참고합니다.
- 제목과 연결 오류가 보이면 이번 차시의 backend와 모델 서버 CMD를 확인합니다. 로그인 차시는 Redis도 실행 중이어야 합니다.
- 설정 파일은 실행한 폴더의 .env를 읽습니다. 다른 차시 .env를 편집한 것은 아닌지 확인합니다.
- 연결·모델 오류는 성공 기록에 넣지 않습니다. 로그인 만료 안내가 나오면 다시 로그인합니다.

</details>

## 4. Vibe 코딩에 유용한 프롬프트

```text
lesson04/main.py의 현재 수정 대상 함수를 확인해 줘.
현재 증상: 새 대화를 눌러도 대화 ID와 말풍선이 그대로다.
검증된 계정과 대화 ID로 기록을 나눕니다.
현재 동작과 기대 동작의 차이를 설명하고 해당 함수 한 곳만 최소 수정해 줘.
로그인·소유권 검사와 기존 성공 기록 방식은 유지해 줘.
수정 전 코드 위치와 수정 후 확인할 입력·화면 결과를 짧게 알려줘.
비밀번호·토큰·.env 값은 출력하지 마.
```

### 복습 과제

A와 B가 서로 다른 학습 주제를 말한 뒤 후속 질문을 하세요. 각 요청의 모델 입력에 상대 계정의 문장이 없는지 확인하고 새 대화 ID가 바뀌는 이유를 설명하세요.

수정한 함수와 직접 확인한 결과를 짧게 남깁니다. 실제 계정 정보나 대화 원문 전체를 제출하지 않습니다.
