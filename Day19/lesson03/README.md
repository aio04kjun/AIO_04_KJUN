# 3차시. FastAPI에 이전 대화와 질문 보내기

## 1. 학습목표

[수업 전 안내](../TODAY_GUIDE.md)를 먼저 확인합니다.

- 화면의 대화 목록을 HTTP 요청 본문에 넣습니다.
- FastAPI가 만든 실제 모델 입력을 확인합니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

말풍선은 남아 있는데 AI가 앞에서 말한 이름을 모릅니다. 화면에 보관하는 것과 서버에 보내는 것은 다른 작업입니다.

이번에는 모델 호출을 FastAPI로 옮깁니다. 화면은 `httpx.post(..., json=payload)`로 질문과 이력을 보냅니다. FastAPI는 JSON을 `ChatInput`으로 검사한 뒤 `body.history`와 `body.question`을 함수에 전달합니다.

| 위치 | 담는 값 | 예 |
| --- | --- | --- |
| 화면의 messages | 성공한 지난 대화 목록 | user와 assistant 두 개 |
| 요청 본문의 history | 서버에 전달할 목록 | 같은 두 개 |
| 서버의 messages | 이번 모델 입력 | system + 지난 두 개 + 현재 질문 |

서버는 이 차시에서 기록을 보관하지 않습니다. 화면이 요청마다 이전 대화를 보내야 합니다. 이 서버는 로그인 없이 본인 PC에서 한 사람이 확인하는 단계이므로 127.0.0.1로 실행합니다.

### 수정 전 위치와 이번에 바꿀 함수

`make_payload()`가 `return {"question": question, "history": []}`를 반환합니다. 화면에는 기록이 있지만 HTTP 요청에는 빈 목록을 넣고 있습니다.

수정할 파일은 **lesson03/main.py**입니다. 아래 함수로 교체합니다. 전체 실행 코드는 [main.py](main.py)에 있으며, 여기는 수정할 부분만 표시합니다.

```python
def make_payload(history, question):
    return {"question": question, "history": history}
```

참고: [공식 대화 상태 안내](https://developers.openai.com/api/docs/guides/conversation-state), [위키독스 챗봇 예제](https://wikidocs.net/352332).

## 3. 코드 제공

### 준비와 실행

Windows CMD에서 현재 차시 폴더로 이동합니다. 기존 수업 가상환경을 사용하거나 처음 한 번만 생성·활성화합니다. [서버 실행 안내](../BACKEND_GUIDE.md)에서 이번 차시에 해당하는 서버를 먼저 준비합니다.

```bat
cd /d C:\AI4\MultiTurn_02_08\lesson03
python -m pip install -r requirements.txt
copy .env.example .env
python -m streamlit run main.py --server.address 127.0.0.1 --server.port 8501
```

패키지를 설치하고 설정 예시를 복사한 뒤 화면 서버를 실행합니다. **기존 .env가 있으면 복사로 덮어쓰지 말고 값을 확인**합니다. 파일 미리보기가 아니라 브라우저의 http://127.0.0.1:8501 에서 실습합니다. 종료는 이 CMD에서 Ctrl+C입니다.

화면 폴더의 .env에는 `API_BASE_URL=http://127.0.0.1:8000`을 사용합니다. 모델 키와 DB 접속 값은 백엔드 폴더의 .env에만 둡니다. 이번 차시는 **backend03**와 연결합니다.

### 실행해 보고 한 곳 바꾸기

1. **새 대화**를 누르고 `내 이름은 민수야.` 다음에 `내 이름이 뭐야?`를 전송합니다. **직전 요청에서 AI에게 보낸 메시지**를 펼치면 시작 코드의 입력에는 system과 현재 질문 두 개만 있습니다.
2. 화면 폴더 lesson03/main.py의 `make_payload()`만 위 코드로 교체합니다. 백엔드 코드는 바꾸지 않습니다.
3. **새 대화**를 누르고 같은 두 문장을 다시 전송합니다. 두 번째 요청에는 system, 앞선 user, 앞선 assistant, 현재 user가 순서대로 있어야 합니다.
4. `방금 네가 한 답변을 더 짧게 말해줘.`를 전송합니다. 이전 assistant 내용도 요청에 포함되어 있는지 펼쳐 확인합니다.

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
lesson03/main.py의 현재 수정 대상 함수를 확인해 줘.
현재 증상: 화면 기록은 있지만 서버에 보낸 history가 빈 목록이다.
화면의 대화 목록을 HTTP 요청 본문에 넣습니다.
현재 동작과 기대 동작의 차이를 설명하고 해당 함수 한 곳만 최소 수정해 줘.
로그인·소유권 검사와 기존 성공 기록 방식은 유지해 줘.
수정 전 코드 위치와 수정 후 확인할 입력·화면 결과를 짧게 알려줘.
비밀번호·토큰·.env 값은 출력하지 마.
```

### 복습 과제

질문뿐 아니라 이전 AI 답변을 가리키는 후속 질문을 만들어 보세요. 모델 입력에서 assistant 메시지 한 개를 찾아 그 역할을 한 문장으로 설명하세요.

수정한 함수와 직접 확인한 결과를 짧게 남깁니다. 실제 계정 정보나 대화 원문 전체를 제출하지 않습니다.
