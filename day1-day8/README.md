# 작은 인사 — Python 방명록

`codex.md`의 요구사항에 따라 Day 01–08 수업의 FastAPI/Pydantic 구성을 유지한 작은 방명록입니다. **Python + FastAPI + Pydantic + SQLite + HTML/CSS**를 사용합니다. 입력란의 맞춤 알림 말풍선에만 작은 JavaScript 파일을 사용합니다. React, Vue, ORM, 외부 DB, 외부 폰트와 유료 API는 사용하지 않습니다. SQLite는 Python에 내장되어 있습니다. 새 외부 패키지는 추가하지 않았습니다.

## 실행

저장소 루트 `C:\AIO_04_kjun`의 PowerShell에서:

```powershell
.\.venv\Scripts\python.exe day1-day8/main.py
```

브라우저에서 <http://127.0.0.1:8000>을 엽니다. 종료는 터미널에서 `Ctrl+C`입니다. HTML을 파일로 직접 열면 글 저장이 동작하지 않으므로 Python 서버로 접속해야 합니다.

별도의 환경이 필요한 경우, Python 3.10 이상을 설치한 뒤 프로젝트 폴더에서 실행합니다. 아래 `pip install`은 기존 수업에서 사용한 패키지를 해당 환경에 준비하는 명령입니다.

```powershell
cd C:\AIO_04_kjun\day1-day8
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 기능과 화면

- 이름(1–24자)과 이야기(1–500자) 등록, 양끝 공백 제거와 서버 검증
- 최신순 목록, 이름·본문 검색, 한 페이지에 6개씩 이동
- SQLite 파일 저장: 서버를 종료해도 영속 디스크의 파일은 유지
- 등록 후 GET 이동으로 새로고침에 따른 POST 재전송 방지
- 검증 실패 시 입력값 유지, 빈 목록·검색 결과 없음·등록 완료 안내
- 빈 값·공백만 입력 후 제출 시 첫 번째 입력란에 세이지 그린 말풍선 표시, 입력을 채우면 해제. 스크립트를 사용할 수 없으면 브라우저 기본 필수 입력 검증과 서버 검증 유지
- 작은 화면에서는 작성 폼과 목록이 세로로 배치되는 반응형 화면
- 키보드 포커스, 입력 레이블, 본문 건너뛰기, 오류 알림과 동작 줄이기 설정 지원

크림색 바탕, 세이지 그린, 여백과 글 중심 카드로 구성했습니다. 봉투 그림은 HTML 안의 SVG로 작성하여 이미지 다운로드나 추가 비용이 없습니다. 예시 글을 실제 데이터처럼 자동 삽입하지 않습니다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `main.py` | 라우팅, Pydantic 검증, SQLite 저장·검색, HTML 응답 |
| `templates/index.html` | 단일 화면과 기본 HTML 폼 |
| `static/style.css` | 색상, 카드, 반응형·접근성 스타일 |
| `static/validation.js` | 필수 입력 안내 말풍선과 오류 입력란 포커스 |
| `test_guestbook.py` | 임시 DB를 사용하는 기능 테스트 |
| `ANALYSIS.md` | 수업 분석과 구현에 적용한 내용 |
| `DEPLOYMENT.md` | 무료 배포 후보, 제약과 실행 설정 |
| `VERIFICATION.md` | 검증 결과와 확인하지 못한 범위 |

## 데이터 구조와 규모

최초 접속 때 `data/guestbook.db`를 만듭니다. `entries` 테이블 하나만 사용하며 외래 키와 관계는 없습니다. DB 경로는 실행 위치에 영향을 받지 않습니다.

| 열 | SQLite 타입 | 용도 |
| --- | --- | --- |
| `id` | INTEGER PRIMARY KEY | 글 번호 |
| `name` | TEXT NOT NULL | 공개 이름 |
| `message` | TEXT NOT NULL | 공개 이야기 |
| `created_at` | TEXT NOT NULL | UTC+09:00 오프셋을 포함한 등록 시각 |

전체 저장 한도는 1,000개, 요청 본문은 8 KiB입니다. 1,000개에 도달하면 기존 글을 삭제하지 않고 새 등록을 거절합니다. 작은 SQLite 파일을 전제로 한 학습용 상한이며, 서비스 제공자의 무료 요금제 보장은 아닙니다. 동시 작성은 SQLite 트랜잭션으로 처리하며, 파일 잠금 대기는 최대 10초입니다. 단일 서버·단일 워커 사용을 권장합니다.

DB 위치를 지정하려면 실행 전 환경변수를 설정합니다. 상대 경로는 프로젝트 폴더 기준입니다.

```powershell
$env:GUESTBOOK_DB = "data/guestbook.db"
.\.venv\Scripts\python.exe main.py
```

로그인, 수정·삭제, 첨부파일, CAPTCHA, 자동 백업은 범위에 포함하지 않았습니다. 공개 이름과 글만 수집하며 연락처를 적지 않도록 화면에서 안내합니다. 자동 도배 방지나 관리 기능이 없는 소규모 학습용 앱입니다. 화면의 출처 검사로 모든 자동 요청이 차단되지는 않습니다.

백업은 서버를 종료한 상태에서 `data/guestbook.db`를 안전한 위치로 복사합니다. 복구도 서버를 종료한 상태에서 수행합니다. `.gitignore`로 DB와 가상환경을 소스 버전 관리에서 제외했습니다.

## 테스트

저장소 루트에서 기존 수업 환경으로 실행합니다. 시스템 임시 폴더 접근 제약을 피하기 위해 테스트용 DB를 프로젝트 안에 만듭니다.

```powershell
New-Item -ItemType Directory -Force day1-day8/.pytest_cache | Out-Null
.\.venv\Scripts\python.exe -m pytest day1-day8/test_guestbook.py -q --basetemp=day1-day8/.pytest_cache/tmp
```

`--basetemp`는 pytest가 매번 비우는 **테스트 전용 경로**입니다. 실제 데이터 디렉터리로 바꾸지 마세요. 새로운 환경에서 테스트하려면 `requirements-dev.txt`를 설치합니다. 테스트는 실행할 때마다 임시 SQLite를 사용하며 실제 방명록 DB를 바꾸지 않습니다.
