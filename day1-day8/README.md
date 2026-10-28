# 작은 인사 — Supabase 방명록

FastAPI/Pydantic 방명록을 Supabase PostgreSQL에 연결합니다. 기존 화면, 작성자 쿠키, 검색, 좋아요, 답글 기능을 유지합니다.

## 실행

Python 3.10 이상 환경에서 저장소 루트 기준으로 실행합니다.

```powershell
python -m pip install -r day1-day8/requirements.txt
python day1-day8/main.py
```

브라우저에서 http://127.0.0.1:8000 을 엽니다.

## 연결과 저장

기본 설정 파일은 `day_11/config.json`입니다. `host`, `port`, `dbname`, `user`, `password`를 읽으며 SSL 연결을 사용합니다. 비밀번호를 소스에 복사하지 않습니다.

다른 설정 파일은 `GUESTBOOK_CONFIG` 환경변수로 지정합니다. 상대 경로는 `day1-day8` 폴더를 기준으로 해석합니다.

앱 최초 요청 시 `public.entries` 테이블을 자동 생성합니다. 계정에는 테이블 생성 및 조회/변경 권한이 필요합니다. 서버에서 직접 PostgreSQL에 연결하며 브라우저에 접속 정보를 전달하지 않습니다.

이전 SQLite 파일은 수정하지 않으며 기존 SQLite 데이터의 자동 이전은 포함하지 않습니다. `GUESTBOOK_DB` 설정은 더 이상 사용하지 않습니다.

글은 최대 1,000개, 이름은 1–24자, 본문은 1–500자입니다. 좋아요와 답글은 JSON 문자열 열에 저장합니다. 글 등록 한도와 소셜 변경은 트랜잭션 및 테이블 잠금으로 보호합니다. DB 연결 제한은 10초, 쿼리 제한은 15초입니다.

## 검증

```powershell
python -m pip install httpx
python day1-day8/verify_supabase.py
```

실제 Supabase에서 연결, 페이지, 등록, 검색, 수정/삭제, 좋아요, 답글 기능을 검증합니다. 테스트 글 변경은 하나의 트랜잭션으로 실행한 뒤 롤백합니다. 테이블 초기화는 유지되며 ID 시퀀스는 증가할 수 있습니다. 이전 `test_guestbook.py`는 SQLite 전용이므로 건너뜁니다.
