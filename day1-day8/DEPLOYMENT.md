# 무료 배포 검토

확인 날짜: **2026-10-23 (한국 시간)**. 실제 서비스 가입이나 배포는 수행하지 않았습니다. `codex.md`의 요청에 따라 무료 서비스 선택을 위한 추천과 배포 방법을 준비했습니다.

## 추천과 판단

| 서비스 | 추천 용도·이유 | 이 앱에서 확인할 점 |
| --- | --- | --- |
| **PythonAnywhere** | SQLite 파일을 계정 디스크에 두고 작은 Python 앱을 호스팅하려는 경우의 우선 검토 후보 | FastAPI용 ASGI 호스팅은 베타. 계정에서 이용 가능 여부와 무료 적용 조건을 확인해야 함 |
| **Render Free** | FastAPI/Uvicorn 실행 절차가 단순한 임시 시연 | 무료 서비스에는 영속 디스크를 연결할 수 없어 재시작·재배포 시 SQLite 글이 사라질 수 있음. 보존이 필요한 방명록에는 부적합 |

**조건부 추천은 PythonAnywhere입니다.** 파일 기반 SQLite 요구와 잘 맞지만, 공식 ASGI 문서는 장기 요금 정책이 정해지지 않았다고 명시합니다. FastAPI + 영구 SQLite + 무료라는 조건이 모든 계정에서 보장된다고 안내할 수는 없습니다. ASGI가 무료 계정에서 제공되지 않으면 유료 업그레이드나 다른 프레임워크 변경을 자동으로 진행하지 말고, 로컬로 사용하며 배포 선택을 다시 검토해야 합니다.

PythonAnywhere 무료 계정 안내에는 CPU 100초, 디스크 512 MiB, 웹 앱 1개·워커 1개·만료 기간 1개월, 콘솔 2개가 명시되어 있습니다. CPU 수치는 모든 웹 요청의 총 처리 시간을 뜻한다고 단정하지 말고 공식 CPU 안내를 함께 확인하세요. 만료 전 갱신과 앱·가상환경·로그·백업을 합친 디스크 사용량 관리가 필요합니다.

이 앱은 외부 API·첨부파일·유료 DB를 사용하지 않고 1,000개로 글 수를 제한합니다. **코드의 작은 규모만으로 호스팅 비용이 0원임을 보장하지는 않습니다.** 트래픽, 계정 조건, 정책 변경 및 ASGI 제공 조건은 배포 시 다시 확인하세요. GitHub Pages처럼 정적 파일만 제공하는 곳에서는 Python과 SQLite 저장을 실행할 수 없습니다.

## PythonAnywhere 배포 준비

1. 무료 계정에서 ASGI 앱 생성 가능 여부와 무료 조건을 먼저 확인합니다.
2. `day1-day8`의 소스를 `/home/YOURUSERNAME/guestbook`에 업로드합니다. 로컬 `.venv`, 캐시와 실제 방명록 DB는 제외합니다. DB를 옮겨야 한다면 서버 종료 후 별도로 백업·복사합니다.
3. 사이트용 가상환경을 만들고 `requirements.txt`를 설치합니다.
4. ASGI 실행 명령으로 아래 예시를 사용합니다. `YOURUSERNAME`과 가상환경 경로를 자신의 값으로 바꿉니다.

```bash
/home/YOURUSERNAME/.virtualenvs/guestbook/bin/uvicorn --app-dir /home/YOURUSERNAME/guestbook --uds ${DOMAIN_SOCKET} main:app --workers 1
```

앱은 기본적으로 `/home/YOURUSERNAME/guestbook/data/guestbook.db`에 저장합니다. `data/` 쓰기 권한과 디스크 잔여 공간을 확인합니다. CSS는 앱의 `/static/style.css` 라우트가 제공하므로 ASGI의 별도 정적 파일 매핑이 필요하지 않습니다. HTTPS 역방향 프록시를 통과할 때는 Uvicorn이 제공자의 신뢰 가능한 프록시 헤더 설정을 따르게 하여 요청 Origin과 앱의 스킴·호스트가 일치하도록 합니다. 출처 검사에서 403이 나면 검사를 끄기 전에 프록시 구성을 확인하세요.

PythonAnywhere의 공식 `pa` 관리 도구 설치와 사이트 생성은 아래 ASGI 안내를 따릅니다. 이는 호스팅 관리 도구이며 앱 의존성에는 포함하지 않았습니다. 로컬 작업에서는 이 도구를 설치하지 않았습니다.

## Render에서 임시 시연할 때

- 서비스 유형: Web Service, 인스턴스: Free
- Root Directory: `day1-day8`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
- 유료 디스크·DB·상위 플랜을 추가하지 않습니다.

무료 서비스는 15분간 요청이 없으면 중지될 수 있으며, 다시 시작할 때 SQLite 데이터가 사라질 수 있습니다. 영구 데이터를 저장할 목적이라면 이 구성을 선택하지 마세요. 무료 Render Postgres로 대체하는 것도 이번의 내장 DB·테이블 하나 요구와 맞지 않아 구현하지 않았습니다.

## 공식 출처

- [PythonAnywhere 무료 계정 기능](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/)
- [PythonAnywhere CPU 사용량 안내](https://help.pythonanywhere.com/pages/CPU/)
- [PythonAnywhere ASGI 배포 베타 — FastAPI와 실행 명령](https://help.pythonanywhere.com/pages/ASGICommandLine/)
- [Render 무료 배포 — 임시 파일시스템과 무료 제한](https://render.com/docs/free)
- [Render 영속 디스크 — 유료 서비스 대상](https://render.com/docs/disks)
