# Day 01–08 분석과 적용

## 분석 결과

폴더와 Python 파일의 구성·import·함수·클래스를 확인하고, 기초 실습, 리팩터링 예제, FastAPI CRUD, Pydantic 검증 및 테스트 파일을 읽어 구현 범위를 정했습니다. 일부 실습은 미완성 코드나 의도적인 오류를 포함하므로 전체 수업 코드를 실행하거나 수정하지 않았습니다.

| 폴더 | 확인한 주요 내용 | 방명록 적용 |
| --- | --- | --- |
| `day_01` | 변수, 조건문, for/while, 리스트, 문자열, 함수 | 등록·조회 함수, 목록 순회, 빈 상태 분기 |
| `day_02` | 조건식, 단락 평가, 컴프리헨션, set/정렬, 문자열·정규식, assert 중심 검증 | 공백 처리, 입력 조건, 목록 생성, 테스트 기대값 |
| `day_03` | 클래스, 캡슐화, 상속·추상화, dataclass, 예외 처리, 함수 분리와 리팩터링 | 입력 모델 클래스와 책임별 작은 함수, 예외 처리. 복잡한 상속 구조는 불필요하여 생략 |
| `day_04` | `day_04_01.py`는 `#git test`만 있는 상태, `login.txt` 파일 존재 | 이 폴더에서 앱 프레임워크는 확인되지 않음. 로그인 파일 내용은 앱에 사용하지 않음 |
| `day_05` | FastAPI·Uvicorn, 경로·쿼리·본문, HTTP 상태, CRUD와 실행 도구 | GET/POST, 쿼리 검색, 서버 실행, HTTP 응답 |
| `day_06` | BaseModel, Field, ConfigDict, 검증·직렬화, 메모리 CRUD | `EntryIn`, 길이 제한, 공백 제거, 추가 필드 거부 |
| `day_07` | asyncio, async/await, httpx, 비동기 요청·오류 처리 | 본문을 비동기로 읽고 동기 SQLite 작업은 FastAPI/Starlette의 스레드에서 처리 |
| `day_08` | Query/Path/Field 경계, 상태 코드, API 테스트, 응답 계약 | 페이지·검색 길이 제한, 잘못된 입력·경계값·저장 결과 테스트 |

`day_06/ch07_fastapi/app.py`의 CRUD 예제, `day_08/lesson_02_parameters/main.py`의 Query 제한, `day_08/lesson_04_ai_test_cases/test_generated.py`의 pytest/TestClient 패턴을 특히 참고했습니다. Day 08의 할인 계산 로직은 방명록과 무관하여 가져오지 않았습니다.

## 단순하게 구현한 흐름

1. `GET /` → SQLite 조회 → Python에서 HTML 생성 → 브라우저 표시
2. 기본 `<form method="post">` → `POST /entries`
3. 요청 크기·형식 확인 → Pydantic 검증 → SQL 매개변수로 저장
4. `303`으로 첫 화면 이동 → 완료 안내와 최신 글 표시
5. 검색·페이지 이동은 `<form method="get">`과 링크로 처리

검색은 SQLite의 `instr`를 사용한 단순 부분 문자열 검색입니다. 1,000개 제한의 작은 앱이므로 별도 검색 엔진이나 검색 알고리즘 패키지가 필요하지 않습니다. 정렬은 `ORDER BY id DESC`, 페이지 이동은 `LIMIT/OFFSET`으로 처리합니다.

## 요청에 따라 추가한 Python 내장 기능

- `sqlite3`: 사용자가 명시한 내장 DB. ORM·외부 DB 서버 없음.
- `html.escape`: 사용자 입력을 HTML 문자로 표시하여 스크립트 실행 방지.
- `urllib.parse.parse_qs/urlencode`: HTML 기본 폼과 검색 URL 처리. `python-multipart` 없이 구현.
- `pathlib`, `datetime`, `contextlib`, `string.Template`, `os`: 파일 경로, 한국 시각, 연결 종료, 단순 문자열 치환, 설정에 사용.

외부 템플릿 엔진, 폼 라이브러리, 인증·암호화 패키지, 새로운 비즈니스 알고리즘을 추가하지 않았습니다. 따라서 추가 라이브러리 선택을 위한 확인 없이 기존 수업 스택과 요청된 내장 기능 안에서 구현했습니다.

사용자 데이터는 HTML 치환 전에 escape하고, 한 번만 치환합니다. SQLite 연결은 요청 사이에 공유하지 않고 작업 후 닫습니다. 저장 한도 확인과 INSERT는 하나의 트랜잭션으로 처리합니다. 테이블 구조는 `entries` 하나입니다.

## 우주 디자인·수정·삭제 확장

후속 요청에 따라 UI를 유리 패널과 세리프 제목의 우주 테마로 변경했습니다. `StaticFiles`는 기존 FastAPI/Starlette에 포함된 정적 파일 기능이며, 새 패키지 없이 PNG·CSS·JavaScript를 제공합니다. `space.js`는 로컬 문구 선택과 모션 정지·재생만 처리하고 CRUD는 HTML 폼과 서버에서 처리합니다.

수정·삭제는 Python 표준 `secrets`의 무작위 토큰, `hashlib.sha256`의 해시와 HttpOnly 쿠키로 작성 브라우저를 확인합니다. `entries.owner_hash` 열을 추가하며 다른 테이블·로그인 시스템·외부 인증을 사용하지 않습니다. 소유 정보가 없는 기존 글에는 권한을 추정해서 부여하지 않습니다. 자세한 사용 제한은 README를 참고하세요.

## 좋아요·답글 확장

표준 `json`으로 한 테이블의 `likes_json`, `replies_json` 열을 직렬화합니다. 관계형 테이블을 늘리지 않고 원글 안에 좋아요 목록과 단일 단계 답글을 저장합니다. 기존 DB는 빈 JSON 목록을 기본값으로 열을 추가하며 원래 데이터를 유지합니다.

좋아요는 단순한 토글 요청 대신 원하는 최종 상태(`true`/`false`)를 받아 같은 요청을 재전송해도 중복 집계하지 않습니다. 같은 브라우저 쿠키의 해시를 식별자로 사용하고 원문 토큰·해시는 응답에 노출하지 않습니다. JavaScript의 같은 출처 fetch는 서버 결과를 받은 뒤 화면을 갱신합니다. 답글 CRUD와 스크립트 없는 좋아요는 HTML POST와 303 이동으로 처리하며 검색어·페이지와 원글 위치를 유지합니다. 각 JSON 변경은 SQLite 트랜잭션 안에서 처리해 동시 요청에 의한 덮어쓰기를 방지합니다.
