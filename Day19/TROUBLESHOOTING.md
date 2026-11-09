# 실행이 안 될 때만 확인하기

## 파일 미리보기와 실행 화면 구분

main.py 링크의 미리보기는 앱이 아닙니다. 파일을 저장한 폴더에서 실행하고 브라우저 주소를 엽니다.

```bat
python -m streamlit run main.py --server.address 127.0.0.1 --server.port 8501
```

브라우저에서 http://127.0.0.1:8501 을 엽니다. 제목도 안 보이면 Ctrl+Shift+R 또는 새 시크릿 창에서 확인합니다. 그래도 같으면 CMD의 오류 마지막 부분을 확인합니다. 실제 토큰·비밀번호가 포함된 내용은 공유하지 않습니다.

## 포트를 사용 중이라는 메시지

이전 Streamlit CMD에서 Ctrl+C로 종료합니다. FastAPI도 8000 포트에 한 개만 실행합니다. 다른 backend로 교체할 때 이전 것을 먼저 종료합니다. 모델 서버의 8080 포트는 별개이므로 유지합니다.

## 다른 main.py를 실행한 것 같은 경우

CMD의 현재 폴더와 파일을 확인합니다.

```bat
cd
python -c "from pathlib import Path; print(Path('main.py').resolve())"
```

표시된 폴더가 현재 차시인지 봅니다. 백엔드는 backend 폴더에서, 화면은 lesson 폴더에서 실행합니다.

## 모델 연결 오류 또는 빈 답변

모델 서버 CMD와 LLM_BASE_URL·LLM_MODEL을 확인합니다. 로컬 별명은 local-chat입니다. 모델 목록은 `curl http://127.0.0.1:8080/v1/models`로 확인합니다. 이 명령이 실패하면 UI 코드보다 모델 서버를 먼저 확인합니다.

## 로그인 실패와 DB 실패

이메일 확인이 필요한 계정은 확인을 마칩니다. 4차시부터 Redis가 필요하며, 6차시부터 DB URI와 `python main.py init` 준비가 필요합니다. 프로젝트 publishable key와 DB 비밀번호는 서로 다른 값입니다. DB URI 비밀번호에 특수문자가 있으면 URI용으로 인코딩된 값을 사용합니다.

## 실패 실습이 작동하지 않는 경우

현재 차시 main.py의 실패 버튼을 누르고 새 질문을 전송합니다. 입력 중인 초안만으로 pending은 생기지 않습니다. 키 이름 fail_next_chat과 api의 try 안에 있는 실패 조건을 확인합니다. 입력창이 잠긴 상태라면 원래 대화에서 재시도하거나 로그아웃해 미확정 상태를 정리합니다.

## 가상환경의 예전 Python 경로 오류

현재 CMD에서 가상환경을 빠져나온 뒤 사용할 Python을 확인합니다.

```bat
deactivate
where python
python --version
```

사용 가능한 Python을 확인한 후 기존 .venv를 별도 이름으로 옮기고 새로 만듭니다. 기존 .env와 코드는 지우지 않습니다.

```bat
ren .venv .venv_backup
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

이미 .venv_backup이 있으면 다른 백업 이름을 사용합니다. 정상 실행되는 환경에서는 이 복구 절차를 진행하지 않습니다.
