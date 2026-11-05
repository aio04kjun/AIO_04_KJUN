# 4교시. 대화 이력을 백엔드로 보내 연속 대화 만들기

## 1. 학습목표

- 화면의 대화 보관과 모델에 전달하는 문맥을 구분한다.
- 이전 user/assistant 메시지와 현재 질문을 함께 백엔드로 전송한다.
- 정상 완료된 대화 쌍만 보관하고 새 대화로 초기화한다.

AI 인터페이스 및 UX 설계에서 이전 Streamlit 상태 관리와 Pydantic 검증을 연속 대화에 적용한다. 현재의 messages 계약과 상태 수명 구분은 이후 Redis 세션·Supabase 이력·에이전트 메모리 학습에 이어진다. 이번 저장 위치는 Streamlit 서버의 브라우저 세션 메모리이며 DB 연동은 아니다.

## 2. 중요 알고리즘 및 코드를 읽을 때 반드시 알아야 할 내용

### 화면에 남기는 일과 모델에 보내는 일

3교시는 현재 질문만 보냈다. 화면에 이전 대화를 출력하는 코드를 추가해도 HTTP 요청이 현재 질문 하나뿐이면 모델은 이전 내용을 받지 못한다. 이번에는 `st.session_state.messages`를 화면 복원에도 쓰고 다음 요청의 본문에도 넣는다.

| 구분 | 이번 처리 | 수명·책임 |
| --- | --- | --- |
| 모델 가중치 | FastAPI의 app.state.model | 서버 프로세스에서 재사용. 대화를 학습해서 저장하지 않음 |
| 화면 이력 | Streamlit의 session_state.messages | 현재 브라우저 연결 세션의 완료된 메시지 |
| 모델 문맥 | 매 요청의 messages | 백엔드가 고정 system 지시와 합쳐 토큰화 |
| Redis·DB | 이번 코드에 없음 | 만료 세션·영속 보관은 후속 구현 |

브라우저 새로고침·새 탭·Streamlit 재시작은 세션 상태를 잃거나 별도 세션을 만들 수 있다. FastAPI만 재시작하고 같은 Streamlit 세션이 유지되면 UI가 다음 요청에 이력을 다시 보내 대화를 이어갈 수 있다. 이는 백엔드가 이력을 저장해서 복원한 것이 아니다.

### 달라진 요청 계약

주소는 3교시와 같은 `/chat/stream`이지만 본문은 prompt에서 messages로 바뀐다. 3·4교시 UI와 서버를 섞지 않는다.

```json
{
  "messages": [
    {"role":"user","content":"내 이름은 민수입니다."},
    {"role":"assistant","content":"안녕하세요, 민수님."},
    {"role":"user","content":"내 이름은 무엇인가요?"}
  ]
}
```

위 assistant 내용은 형식 설명용 예시다. 실제 화면은 모델이 생성해 완료한 assistant 답변을 저장해 보낸다. 백엔드는 각 `Message.model_dump()`를 통해 Pydantic 객체를 딕셔너리로 바꾼다. `model_dump_json()`으로 JSON 문자열을 만들어 중첩해서 넣지 않는다.

`role`은 user/assistant만 허용하고 system 지시는 백엔드가 붙인다. 메시지 순서는 user → assistant → user이며 마지막은 현재 질문이어야 한다. `@model_validator(mode="after")`가 본문 검증 후 이를 확인한다. 같은 user가 연속되거나 assistant로 시작하면 422다.

### 대화 한 쌍을 반영하는 시점

1. 이전 완료 이력과 현재 질문을 더해 임시 `candidate`를 만든다.
2. 그 목록을 HTTP로 전송하고 스트리밍 답변을 표시한다.
3. done을 받고 정상 반환한 경우에만 user/assistant 한 쌍을 원본 이력에 넣는다.
4. 실패하면 이전 이력을 그대로 둔다. 화면에 보인 부분 답변을 다음 모델 문맥에 넣지 않는다.

이는 DB 트랜잭션을 실행한다는 뜻이 아니라 화면 상태를 갱신하는 간단한 규칙이다. 이 규칙이 없으면 실패한 user만 남아서 다음 입력 때 user/user 순서가 될 수 있다.

### CPU 실습의 고정 범위

| 항목 | 제한 |
| --- | --- |
| 화면의 현재 질문 | 공백 제거 후 1~500자 |
| API 메시지 하나 | user/assistant, 내용 1~2000자 |
| 요청 메시지 수 | 최대 9개: 과거 4쌍+현재 질문 |
| 전체 입력 | system·대화 템플릿 포함 최대 512토큰 |
| 새 답변 | 최대 96토큰 |

다섯 번의 질문을 완료하면 새 대화로 시작한다. 메시지 수가 적어도 전체 토큰 제한을 먼저 만날 수 있다. 이번에는 오래된 이력을 몰래 잘라내지 않고 422로 알려 준다. 다음 단계에서 토큰 예산에 맞게 오래된 대화 쌍을 제외하는 방법으로 확장한다.

### 참고 자료와 반영

조사일 2026-11-05. 표시되지 않은 자료 수정일·패키지 버전은 확인하지 못했다.

| 검색·읽은 자료 | 참고한 코드 | 이번 반영·변경 |
| --- | --- | --- |
| `site:wikidocs.net streamlit session_state messages chat_input` → [채팅 UI 요소](https://wikidocs.net/352275) | messages 초기화 → 과거 메시지 다시 그리기 → 새 입력·응답 추가 | lesson04 `main`. 에코를 실제 HTTP 모델 스트림으로 바꾸고 정상 완료 후 한 쌍 반영 |
| [Streamlit session_state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) | 사용자 세션별 재실행 사이 값 유지 | 세션 수명·초기화 설명의 공식 근거 |
| [Transformers 4.57.1 Chat templates](https://huggingface.co/docs/transformers/v4.57.1/chat_templating) | role/content 메시지 배열을 대화 토큰으로 변환 | backend04 `prepare_inputs` |
| [FastAPI Request Body](https://fastapi.tiangolo.com/tutorial/body/), [Pydantic model validators](https://docs.pydantic.dev/latest/concepts/validators/#model-validators) | 중첩 본문 모델과 모델 단위 순서 검증 | `Message`, `ChatRequest.check_order` |
| [Streamlit 1.50 write_stream](https://docs.streamlit.io/1.50.0/develop/api-reference/write-magic/st.write_stream) | 텍스트 스트림의 최종 문자열 반환 | 완료 응답을 assistant 메시지로 반영 |

## 3. 코드 제공

### 준비: 실행 폴더와 Python

압축을 풀어 `C:\AI4\Day17\hf_chat` 아래에 `backend04`와 `lesson04`가 나란히 있다고 가정한다. 다른 위치에 풀었다면 아래 경로를 바꾼다. VSCode 터미널의 기본 프로필을 **Command Prompt**로 선택하고 새 CMD 터미널을 연다. 아래 명령은 CMD 기준이다.

현재 수업의 정상 가상환경 `C:\AI4\.venv`를 재사용한다. 아래 명령은 폴더를 이동하고 그 환경의 Python을 선택한 뒤 실제 경로·버전을 확인한다.

```bat
cd /d C:\AI4\Day17\hf_chat\backend04
C:\AI4\.venv\Scripts\activate
python --version
python -c "import sys; print(sys.executable)"
```

`cd /d`는 드라이브까지 포함해 이동한다. `activate`는 현재 CMD에 가상환경을 선택한다. `--version`은 Python 버전 조회, `-c`는 따옴표 안의 Python 코드 실행이다. 출력 경로가 `C:\AI4\.venv\Scripts\python.exe`인지 확인한다. x64 Python 3.11/3.12를 권장한다.

외부 Python 경로를 찾지 못하는 기존 가상환경 오류가 있으면 [백엔드 안내의 환경 복구](../BACKEND_GUIDE.md#가상환경-복구)를 먼저 따른다. 정상 환경을 다시 만들 필요는 없다.

### 패키지와 설정

백엔드 CMD에서 CPU용 PyTorch와 이번 차시에 필요한 패키지를 설치한다. 이미 같은 버전이 설치되어 있으면 재사용한다.

```bat
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip install -r ..\lesson04\requirements.txt
```

`-m pip`는 현재 Python의 설치기를 실행한다. `==`는 버전 지정이고 `--index-url`은 CPU 패키지 저장소다. `-r`은 설치 목록 파일을 읽으며 `..`은 상위 폴더를 뜻한다. 첫 목록은 백엔드, 두 번째 목록은 화면의 직접 의존성이다. 모든 하위 패키지까지 고정한 잠금 파일은 아니다.

설치 상태를 확인한다. 마지막 `False`는 CUDA GPU를 사용하지 않는다는 뜻이며 정상이다.

```bat
python -c "import torch, transformers, fastapi, streamlit; print(torch.__version__, transformers.__version__, fastapi.__version__, streamlit.__version__); print(torch.cuda.is_available())"
```

버전은 PyTorch 2.8.0(CPU 접미사 가능), Transformers 4.57.1, FastAPI 0.118.0, Streamlit 1.50.0을 기준으로 한다. backend requirements는 Pydantic 2.12.3도 지정한다. **PyTorch 누락**이면 모델을 실행할 수 없다. **accelerate 요구 오류**는 기존 코드에 `device_map="auto"`가 남았는지 확인한다. 이 백엔드는 `dtype=torch.float32`와 `model.to("cpu")`를 사용한다.

백엔드 설정 예시를 복사한다. 이미 .env가 있으면 기존 내용을 먼저 확인하고 덮어쓰지 않는다.

```bat
copy .env.example .env
```

`copy`는 CMD의 파일 복사 명령이다. 백엔드 .env는 다음과 같다.

```dotenv
HF_MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct
MODEL_DIR=../models/qwen2.5-0.5b-instruct
```

`HF_MODEL_ID`는 다운로드 저장소 ID, `MODEL_DIR`은 모델 파일이 든 실제 폴더다. 상대 경로는 **각 백엔드 main.py의 폴더 기준**이며, 기본값은 묶음 루트의 같은 모델 폴더를 가리킨다. 세 백엔드가 모델 파일을 공유하지만 서버 프로세스·RAM까지 공유하는 것은 아니다.

1차시에서 모델을 별도 폴더로 받았다면 `MODEL_DIR`만 그 폴더의 절대 경로로 바꾼다. 예: `MODEL_DIR=C:/AI4/Day17/models/qwen2.5-0.5b-instruct`. 그 안에 config.json·tokenizer.json·model.safetensors 등이 있어야 한다. main1.py가 모델 ID로 자동 다운로드한 **Hub 캐시**와 이 폴더는 다를 수 있다. 경로를 모르면 기본 설정을 유지하고 아래 다운로드 명령으로 준비한다.

파일이 준비되지 않았을 때 백엔드 폴더에서 실행한다. 모델 다운로드는 최초에만 인터넷이 필요하며 설치·다운로드는 수업 시작 전에 완료한다.

```bat
python main.py download
```

`download`는 이 main.py가 argparse로 구현한 명령이다. `parse_args()`가 값을 확인한 뒤 `snapshot_download()`가 필요한 파일을 MODEL_DIR에 저장한다. 완료 문구가 나온 후 서버를 실행한다. 모델 폴더·가상환경·실제 .env는 ZIP에 포함하지 않는다. 약 0.5B 모델의 CPU float32 실행이며 RAM 16GB를 권장한다. 8GB는 다른 앱을 닫고 사전 실행 확인이 필요하다. 기본 실습에 양자화·OpenAI API·llama.cpp·Ollama는 사용하지 않는다.

`load_dotenv(override=False, interpolate=False)`가 .env를 로딩하고 `os.getenv()`가 값을 조회한다. 필수 키 누락·공백은 오류다. 기존 프로세스 환경변수가 .env보다 우선하며, .env 없이 환경변수만 제공해도 동작한다. `${...}` 문자열 치환은 하지 않는다. 공백이나 #이 포함된 설정은 따옴표로 감싼다. .env를 바꾸면 해당 프로세스를 재시작한다.

### 터미널 A: 백엔드 실행

다른 차시의 백엔드를 Ctrl+C로 중지한 뒤, `backend04` CMD에서 실행한다.

```bat
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

| 부분 | 의미 |
| --- | --- |
| `-m uvicorn` | 현재 Python에서 ASGI 서버 실행 |
| `main:app` | 현재 폴더 main.py의 FastAPI 객체 app |
| `--host 127.0.0.1` | 현재 PC에서만 접속할 주소 |
| `--port 8000` | 백엔드 접속 포트 |
| `--workers 1` | 모델을 로드하는 서버 프로세스를 하나로 제한 |

모델 로딩 뒤 `CPU 모델 준비 완료`, 이어서 Uvicorn의 `Application startup complete`를 확인한다. 준비 완료 전에 UI에서 질문을 보내지 않는다. `--reload`나 여러 worker를 추가하면 재시작·메모리 증가 원인이 될 수 있으므로 이 실습에서는 사용하지 않는다.

### 터미널 B: Streamlit 실행

새 CMD 터미널에서 화면 폴더로 이동하고 **같은 가상환경**을 활성화한다. 터미널 A는 계속 실행 중이어야 한다.

```bat
cd /d C:\AI4\Day17\hf_chat\lesson04
C:\AI4\.venv\Scripts\activate
copy .env.example .env
```

UI .env의 키는 하나다.

```dotenv
BACKEND_URL=http://127.0.0.1:8000
```

이는 모델 저장소 주소가 아니라 **현재 차시 FastAPI 주소**다. UI는 PyTorch 모델을 로딩하지 않는다. 같은 폴더의 main.py를 Streamlit 실행기로 실행한다.

```bat
python -m streamlit run main.py --server.address 127.0.0.1 --server.port 8501
```

`-m streamlit`은 현재 Python의 화면 실행기, `run main.py`는 실행할 화면 파일이다. `--server.address`와 `--server.port`는 Streamlit의 접속 주소와 포트다. [http://127.0.0.1:8501](http://127.0.0.1:8501)에 접속한다. `python main.py`로 실행하면 정상 Streamlit 서버가 시작되지 않는다.

### 종료와 재시작

각 터미널에서 Ctrl+C로 중지한다. 브라우저를 닫는 것만으로 서버가 종료되지는 않는다. 재실행할 때는 해당 폴더에서 가상환경을 활성화하고 서버 명령을 다시 입력한다. 모델 파일이 있으면 다시 다운로드하지 않는다. 8000 포트 충돌은 이전 백엔드를, 8501 충돌은 이전 Streamlit을 먼저 중지하여 해결한다.

### 파일 안내

| 파일 | 역할 |
| --- | --- |
| `lesson04/main.py` | 입력·HTTP 호출·응답 표시를 통합한 전체 화면 코드 |
| `backend04/main.py` | 검증·로컬 모델 실행·응답 처리를 통합한 전체 서버 코드 |
| 각 폴더의 `.env.example` | 해당 프로세스 설정 예시 |
| 각 폴더의 `requirements.txt` | 해당 프로세스의 직접 의존성 설치 목록 |
| 각 폴더의 `.gitignore` | 실제 설정·가상환경·캐시를 Git에서 제외 |
| `lesson_scope.json` | 코드 범위와 호출 근거를 기록한 내부 품질 자료. 실행 설정이 아님 |

화면과 서버는 **별도 프로세스의 진입 파일**이므로 각각 main.py 하나로 구성한다. 서로의 Python 파일을 import하지 않고 HTTP로 통신한다. [BACKEND_GUIDE.md](../BACKEND_GUIDE.md)에 실제 연결 표·코드 차이·전환 순서가 있다. 아래 발췌를 조립하지 말고 제공된 main.py를 실행한다.


### 백엔드 교체와 대화 확인

backend03을 중지하고 backend04를 실행한다. [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)에서 `POST /chat/stream`의 본문 필드가 messages인지 확인한다. lesson04 화면에서 차례로 입력한다.

```text
내 이름은 민수입니다. 짧게 인사해 주세요.
```

첫 답변이 완전히 끝난 다음 입력한다.

```text
내 이름은 무엇인가요?
```

이전 말풍선이 남고 두 번째 요청에 앞의 user/assistant가 포함되어야 한다. 작은 모델이 이름을 잘못 답하면 문맥 전송 자체가 실패했는지와 모델이 정보를 활용하지 못했는지를 구분한다. 전송 목록을 코드와 Swagger의 합성 예제로 확인하고 답변 품질은 별도로 판단한다.

### 핵심 로직

UI `main()`은 이력 원본을 즉시 바꾸지 않고 현재 요청 목록을 만든다.

```python
candidate = st.session_state.messages + [{"role": "user", "content": prompt}]
```

스트림 함수가 done과 본문을 확인하고 정상 반환했을 때만 한 쌍을 반영한다.

```python
if answer is not None:
    st.session_state.messages = candidate + [{"role": "assistant", "content": answer}]
```

`st.write_stream`은 문자열 조각으로만 구성된 스트림을 끝까지 소비하면 최종 문자열을 반환한다. 중간 예외이면 대입이 완료되지 않아 answer는 None으로 남는다. 응답을 생성하기 전에 assistant 빈 문자열을 이력에 미리 추가하지 않는다.

### 직접 검증

| 확인 | 조작과 완료 기준 |
| --- | --- |
| 문맥 전달 | 이름 소개 → 이름 질문. 화면 누적과 요청의 과거 메시지 전달을 함께 확인 |
| 초기화 | 새 대화 버튼 클릭. 화면 이력이 비고 다음 요청은 현재 user 한 개로 시작 |
| 순서 검증 | Swagger에서 user/user/user를 보내 422 확인 |
| 역할 검증 | system을 본문에 보내면 422. 서버의 고정 system 지시와 구분 |
| 계약 불일치 | backend03을 연결하면 messages 본문이 거절됨. backend04로 복구 |
| 실패 시 이력 | 정상 대화 후 백엔드를 중지하고 질문. 오류 후 백엔드 재시작·새 질문 시 실패한 질문이 이전 이력에 없음 |
| 입력 예산 | 짧은 질문을 반복하다 512토큰 초과 안내가 나오면 새 대화로 시작 |

새 대화는 이 화면의 이력만 비운다. 모델 파일 삭제·모델 재학습·다른 탭의 기록 삭제·DB 삭제를 수행하지 않는다. 자동 저장·재로그인 복원·영속 기억으로 설명하지 않는다.

### 검증 범위와 남은 한계

Linux x64·Python 3.12에서 torch 2.8.0+cpu / Transformers 4.57.1 / FastAPI 0.118.0 / Pydantic 2.12.3 / Uvicorn 0.37.0 / Streamlit 1.50.0 / Requests 2.32.5로 확인했다. 실제 다운로드한 Qwen 모델을 `HF_HUB_OFFLINE=1`·`local_files_only=True` 조건에서 실행했다.

- 실제 Uvicorn localhost HTTP 요청과 Streamlit AppTest의 모델 답변 표시를 확인했다.
- 백엔드 중단 시 UI 오류 표시와 잘못된 입력의 422 응답을 확인했다.
- 여섯 코드의 설정 누락·공백·.env 특수문자·환경변수 우선순위·.env 없이 환경변수만 제공·다른 작업 폴더에서 모델 경로 해석을 확인했다.
- 파일/API 범위 감사, 발췌와 코드의 일치, ZIP의 차시 README·복습 과제·연결 표·원본 바이트 일치와 압축 무결성을 검사했다.

실제 Streamlit 두 번째 요청에 첫 user·실제 assistant 답변·현재 user가 함께 들어가는 것을 확인했다. 이름 후속 질문의 실제 답변에 `민수`가 포함되었다. 새 대화 초기화와 서버 중단 뒤 실패한 질문이 이력에 반영되지 않는 것도 확인했다. 잘못된 역할·순서·빈 목록·입력 토큰 초과는 422로 거절했다.

messages[-1:]로 마지막 질문만 보내는 오류 활동과 전체 messages로 복구한 결과는 합성 HTTP 응답을 사용해 전송 목록의 개수·순서로 검사했다. 실제 모델의 연속 대화 검증과 분리한 요청 구성 시험이다.


`done`은 생성 호출과 전송이 정상 종료되었다는 뜻이다. 문장의 완결성·정답·사실성을 보장하지 않는다. 최대 96토큰에 도달하면 문장이 중간에 끝날 수 있다.

Windows 설치·DLL 상태·실제 브라우저 조작·수업 PC의 속도와 RAM 사용량은 직접 검증하지 않았다. 수업 PC에서 위 명령으로 짧은 질문을 사전 실행한다. 작은 0.5B 모델은 한국어 표현과 개념 설명·문맥 활용이 부정확할 수 있다. UI에서 출력되었다는 사실과 답변의 정답 여부는 구분한다. 모델 파일만 로컬에서 읽으며, 물리적인 네트워크 차단 시험은 별도다.


## 4. Vibe 코딩에 유용한 프롬프트

### 기억의 실제 위치 분석

```text
lesson04/main.py와 backend04/main.py를 읽어 줘.
첫 질문 '내 이름은 민수입니다'와 두 번째 질문 '내 이름은 무엇인가요?'를 예로 들어 messages가 어떻게 달라지는지 설명해 줘.
화면의 session_state, HTTP 요청의 문맥, 백엔드의 모델 가중치를 구분해 줘.
새 탭·새 대화·백엔드 재시작·Streamlit 재시작 시 무엇이 남는지 코드 근거와 함께 설명해 줘.
코드를 바꾸지 말고 .env 내용·키·개인정보는 읽거나 출력하거나 외부에 전송하지 마.
```

### AI 디버깅: 화면 기록은 있는데 문맥을 잃는 문제

수정 전 파일을 보관하고 UI `request_stream()`의 `json={"messages": messages}` 한 곳을 `json={"messages": messages[-1:]}`로 바꾼다. 두 차례 대화 후 화면에는 이력이 있지만 전송에는 마지막 질문만 남는지 확인한다. 모델이 우연히 답을 맞히는 경우도 있으므로 답변 문구 하나만으로 검증하지 않는다.

```text
lesson04 화면에는 이전 대화가 보이지만 백엔드가 이름 소개를 받지 못한다.
json 요청을 만드는 부분에서 messages와 messages[-1:]의 차이를 합성 대화로 비교해 줘.
화면 출력 코드를 바꾸거나 이름을 하드코딩하지 말고 요청 목록 전달만 최소 수정해 줘.
실패한 요청이 원본 이력에 추가되지 않는 현재 동작은 보존해 줘.
수정 전후 요청의 메시지 수와 순서로 검증하고 실제 실행하지 못한 항목은 밝혀 줘.
.env 내용·키·개인정보는 읽거나 출력하거나 외부에 전송하지 마.
```

원래 `messages` 전체 전달로 복구한 뒤 같은 순서를 실행한다.

### 복습 과제

가상의 이름·좋아하는 언어를 짧게 소개하고 두 번의 후속 질문을 한다. 이어 새 대화를 눌러 초기화한다. 완료 기준은 정상 대화 쌍의 수, 후속 요청에 포함되는 이력, 초기화 후 첫 요청 구조를 설명할 수 있는 것이다. 제출 증거는 개인정보 없는 화면과 요청 목록 예시다. 실제 .env·모델 파일은 제출하지 않는다.
