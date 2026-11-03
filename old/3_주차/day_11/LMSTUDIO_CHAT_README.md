# VS Code에서 LM Studio와 채팅하기

Python 3.10 이상에서 추가 패키지 없이 실행하는 터미널 채팅 프로그램입니다.
기존 `lms_my.py`, `lms_my_02.py`는 수정하지 않습니다.

## 실행

현재 PC처럼 `python` 명령이 PATH에 없는 환경에서는 VS Code PowerShell 터미널에서
`./day_11/run_chat.ps1`을 실행하세요. Python, py, Codex에 포함된 Python 순으로 찾습니다.
예: `./day_11/run_chat.ps1 --url http://localhost:1234/v1`

1. LM Studio를 실행하고 사용할 채팅 모델을 다운로드한 뒤 로드합니다.
2. LM Studio의 **Developer** 화면에서 **Start Server**로 서버를 켭니다.
3. VS Code에서 `C:\AIO_04_kjun` 폴더를 열고 **터미널 → 새 터미널**을 선택합니다.
4. 다음 명령을 실행합니다.

```powershell
python day_11/lmstudio_chat.py
```

기존 예제에 맞춰 기본 포트는 **1235**입니다. LM Studio가 1234 포트에서 실행 중이라면:

```powershell
python day_11/lmstudio_chat.py --url http://localhost:1234/v1
```

`python` 명령이 없다면 `py`를 사용하세요. 모델이 여러 개라면 번호로 선택합니다.
이 프로그램은 VS Code 터미널에서 실행됩니다. VS Code 확장 프로그램은 아닙니다.
LM Studio 자체를 자동 실행하거나 서버 설정을 변경하지 않습니다.

## 사용법

- 질문 입력 후 Enter: 이전 대화 내용과 함께 전송하고 실시간 답변 표시
- `/clear`: 대화 기록 초기화 (모델의 문맥이 가득 찬 경우에도 사용)
- `/save`: `day_11/chat_logs/`에 UTF-8 JSON으로 대화 저장
- `/exit` 또는 Ctrl+C: 종료

저장 명령을 실행하지 않은 대화는 프로그램 종료 시 사라집니다.
오류가 난 질문과 불완전한 답변은 다음 요청의 대화 기록에 포함하지 않습니다.
응답 읽기 타임아웃은 120초, 최대 생성 길이는 요청당 2048토큰입니다.
모델 전용 문맥 제한은 다르므로 긴 대화에서는 `/clear`를 사용하세요.

## 연결 확인 및 설정

```powershell
python day_11/lmstudio_chat.py --check
python day_11/lmstudio_chat.py --model "목록에 표시된 정확한 모델 ID"
```

서버 인증을 켰다면 토큰을 코드에 적지 않고 환경 변수로 전달합니다.

```powershell
$env:LM_STUDIO_API_KEY = "LM Studio에서 발급한 토큰"
$env:LM_STUDIO_URL = "http://localhost:1235/v1"
python day_11/lmstudio_chat.py
```

연결 거부: 서버 시작 여부와 포트를 확인하세요. HTTP 401: 토큰을 확인하세요.
모델 오류: 채팅용 모델이 로드됐는지 확인하세요. `/models` 목록에는 환경에 따라
로드 가능한 모델도 포함될 수 있습니다. 자동 로드가 꺼져 있다면 LM Studio에서 직접 로드하세요.

요청은 설정한 서버 주소의 `/v1/models`, `/v1/chat/completions`로 전송됩니다.
기본 주소는 로컬이며 클라우드 AI API는 호출하지 않습니다.

공식 문서: https://lmstudio.ai/docs/developer/openai-compat
