"""2~8차시 UI가 사용하는 실제 Supabase Auth·PostgreSQL·Redis 백엔드."""
# 표준 기능: CLI 입력, 환경설정, 토큰을 노출하지 않는 키 이름, 시간, UUID.
import argparse
import hashlib
import os
import time
from typing import Annotated
from uuid import UUID, NAMESPACE_URL, uuid5

# HTTPX와 Supabase SDK가 실제 Auth 통신·검증을 맡는다.
import httpx
from supabase import AuthApiError, AuthRetryableError, create_client
from supabase.client import ClientOptions
from dotenv import load_dotenv
# PostgreSQL과 Redis는 별도 저장소다. SQLite나 메모리 모드로 전환하지 않는다.
import psycopg
from psycopg.rows import dict_row
from redis import Redis, RedisError
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr

# 반드시 backend 폴더에서 실행한다. 기존 환경변수 우선, ${...} 치환 안 함.
load_dotenv(".env", override=False, interpolate=False)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
DB_URL = os.getenv("SUPABASE_DB_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
TTL_TEXT = os.getenv("SESSION_TTL_SECONDS", "")
for name, value in {"SUPABASE_URL": SUPABASE_URL, "SUPABASE_PUBLISHABLE_KEY": SUPABASE_KEY,
                    "SUPABASE_DB_URL": DB_URL, "REDIS_URL": REDIS_URL,
                    "SESSION_TTL_SECONDS": TTL_TEXT}.items():
    if not value.strip():
        raise RuntimeError(f"{name} 설정이 필요합니다.")
if not SUPABASE_URL.startswith("https://"):
    raise RuntimeError("SUPABASE_URL은 https 프로젝트 주소여야 합니다.")
if not REDIS_URL.startswith(("redis://", "rediss://")) or "?" in REDIS_URL:
    raise RuntimeError("REDIS_URL은 쿼리 옵션 없는 Redis URI여야 합니다.")
try:
    SESSION_TTL_SECONDS = int(TTL_TEXT)
except ValueError:
    raise RuntimeError("SESSION_TTL_SECONDS는 양의 정수여야 합니다.") from None
if SESSION_TTL_SECONDS <= 0:
    raise RuntimeError("SESSION_TTL_SECONDS는 양의 정수여야 합니다.")

app = FastAPI(title="사용자별 대화 이력 실습")
# auto_error=False: 헤더 누락도 아래 의존성에서 401로 통일한다. JWT 검증 기능은 아니다.
bearer = HTTPBearer(auto_error=False)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=1, max_length=254)
    # 비밀번호는 strip하지 않고, 검증 오류와 repr에 원문이 나오지 않도록 한다.
    password: SecretStr = Field(min_length=1, max_length=1024)


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    content: str = Field(min_length=1, max_length=1000)
    request_id: UUID  # 같은 저장을 다시 확인할 때는 같은 ID를 사용한다.


# 등록 시점에는 실행되지 않는다. 요청 입력 검사가 실패했을 때 FastAPI가 호출한다.
@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):
    # 비밀번호 등 원본 input 값을 응답에 포함하지 않는다.
    errors = [{"loc": e["loc"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(psycopg.Error)
async def database_error(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "DB 연결과 테이블 준비를 확인하세요."})


@app.exception_handler(RedisError)
async def redis_error(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "Redis 연결을 확인하세요."})


def make_client(http_client):
    # 요청마다 새 SDK 객체를 쓴다. 한 사용자의 인증 상태를 전역으로 공유하지 않는다.
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(
        persist_session=False,  # SDK 저장소 기록을 끈다. 토큰 발급 자체를 끄는 옵션이 아니다.
        auto_refresh_token=False,  # 백그라운드 자동 갱신을 끄고 만료 시 재로그인한다.
        httpx_client=http_client,  # 호출자의 timeout을 재사용한다. 호출자의 with에서 닫는다.
    ))


def raise_auth_error(exc):
    # 자격증명 오류와 인증 서비스 장애를 구분한다. 원문은 응답에 넣지 않는다.
    if exc.code in ("invalid_credentials", "bad_jwt", "user_not_found", "user_banned",
                    "session_not_found", "jwt_expired"):
        raise HTTPException(401, "로그인 정보 또는 토큰을 확인하세요.") from None
    if exc.code == "email_not_confirmed":
        raise HTTPException(403, "이메일 확인을 완료하세요.") from None
    if exc.status == 429:
        raise HTTPException(429, "인증 요청이 많습니다. 잠시 후 다시 시도하세요.") from None
    raise HTTPException(503, "인증 서비스 상태와 프로젝트 설정을 확인하세요.") from None


def connect_db():
    return psycopg.connect(
        DB_URL,  # Supabase Connect의 PostgreSQL Session pooler URI.
        connect_timeout=5,  # 연결 수립 제한(초). SQL 전체 수행 시간 제한은 아니다.
        sslmode="require",  # 원격 DB 통신에 TLS를 요구한다.
        row_factory=dict_row,  # 결과를 컬럼 이름이 있는 딕셔너리로 받는다.
    )


def connect_redis():
    return Redis.from_url(
        REDIS_URL,
        decode_responses=True,  # GET을 bytes 대신 str로 받는다. 기본값은 False다.
        socket_connect_timeout=3,  # 연결 수립 대기 제한(초).
        socket_timeout=3,  # 응답 대기 제한(초).
    )


def session_key(token):
    # 토큰 원문을 Redis 키 이름으로 노출하지 않는다. 해시는 JWT 검증을 대신하지 않는다.
    return "kdt:user-chat:session:" + hashlib.sha256(token.encode()).hexdigest()


def read_token(credentials):
    if credentials is None:
        raise HTTPException(401, "로그인이 필요합니다.")
    return credentials.credentials


def require_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    token = read_token(credentials)
    with connect_redis() as client:
        registered_id = client.get(session_key(token))
    if registered_id is None:
        raise HTTPException(401, "로그인 세션이 없거나 만료되었습니다.")
    try:
        # 단순 디코딩 결과를 믿지 않고 Auth 서버에 토큰을 보내 사용자 정보를 검증한다.
        with httpx.Client(timeout=10.0) as http_client:
            result = make_client(http_client).auth.get_user(token)
    except AuthApiError as exc:
        raise_auth_error(exc)
    except (AuthRetryableError, httpx.HTTPError):
        raise HTTPException(503, "인증 서비스와 통신할 수 없습니다.") from None
    if result is None or result.user is None or str(result.user.id) != registered_id:
        raise HTTPException(401, "사용자를 확인할 수 없습니다.")
    # user.id는 요청 본문의 owner_id가 아니라 검증된 Auth 결과다.
    return {"id": registered_id, "email": result.user.email}


@app.post("/auth/login")
def login(body: LoginInput, response: Response):
    try:
        with httpx.Client(timeout=10.0) as http_client:
            result = make_client(http_client).auth.sign_in_with_password({
                "email": body.email.strip(), "password": body.password.get_secret_value(),
            })
    except AuthApiError as exc:
        raise_auth_error(exc)
    except (AuthRetryableError, httpx.HTTPError):
        raise HTTPException(503, "인증 서비스와 통신할 수 없습니다.") from None
    if result.session is None or result.user is None or result.session.expires_at is None:
        raise HTTPException(502, "인증 응답을 확인할 수 없습니다.")
    # Redis 세션이 원래 JWT보다 오래 살아남지 않도록 더 짧은 수명을 사용한다.
    ttl = min(SESSION_TTL_SECONDS, int(result.session.expires_at - time.time()))
    if ttl <= 0:
        raise HTTPException(401, "로그인 세션이 만료되었습니다. 다시 로그인하세요.")
    token = result.session.access_token
    with connect_redis() as client:
        client.set(session_key(token), str(result.user.id), ex=ttl)  # EX로 초 단위 고정 수명 지정.
    response.headers["Cache-Control"] = "no-store"
    # refresh_token을 UI에 전달하지 않는다. 이번 단원은 재로그인 정책이다.
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl,
            "user_id": str(result.user.id), "email": result.user.email}


@app.get("/me")
def me(user: Annotated[dict, Depends(require_user)],
       credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    with connect_redis() as client:
        ttl = client.ttl(session_key(read_token(credentials)))
    if ttl == -2:
        raise HTTPException(401, "로그인 세션이 만료되었습니다.")
    if ttl == -1:
        raise HTTPException(503, "세션 만료 설정을 확인하세요.")
    return {**user, "ttl": ttl}  # 조회 시점의 남은 초. 조회는 수명을 연장하지 않는다.


@app.post("/auth/logout")
def logout(user: Annotated[dict, Depends(require_user)],
           credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    # 이 앱의 허용 목록만 제거한다. Supabase의 다른 앱/기기 세션 전체를 종료하지 않는다.
    with connect_redis() as client:
        client.delete(session_key(read_token(credentials)))
    return {"ended": True, "user_id": user["id"]}


@app.get("/conversations")
def list_conversations(user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        return conn.execute(
            """SELECT id, title, created_at FROM kdt_user_chat.conversations
               WHERE owner_id = %s ORDER BY created_at, id""", (UUID(user["id"]),),
        ).fetchall()


@app.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: UUID, user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        room = conn.execute(
            "SELECT id FROM kdt_user_chat.conversations WHERE id = %s AND owner_id = %s",
            (conversation_id, UUID(user["id"])),
        ).fetchone()
        if room is None:
            raise HTTPException(404, "대화를 찾을 수 없습니다.")
        return conn.execute(
            """SELECT m.id, m.role, m.content, m.created_at
               FROM kdt_user_chat.messages m JOIN kdt_user_chat.conversations c
               ON c.id = m.conversation_id WHERE c.id = %s AND c.owner_id = %s ORDER BY m.id""",
            (conversation_id, UUID(user["id"])),
        ).fetchall()


@app.post("/conversations/{conversation_id}/messages")
def save_message(conversation_id: UUID, body: MessageInput,
                 user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        # 소유권 검사 후 같은 DB 트랜잭션에서 저장한다. UI의 선택만 믿지 않는다.
        found = conn.execute(
            "SELECT id FROM kdt_user_chat.conversations WHERE id = %s AND owner_id = %s",
            (conversation_id, UUID(user["id"])),
        ).fetchone()
        if found is None:
            raise HTTPException(404, "대화를 찾을 수 없습니다.")
        row = conn.execute(
            """INSERT INTO kdt_user_chat.messages (conversation_id, role, content, request_id)
               VALUES (%s, 'user', %s, %s) ON CONFLICT (conversation_id, request_id)
               DO NOTHING RETURNING id, role, content, created_at""",
            (conversation_id, body.content, body.request_id),
        ).fetchone()
        replayed = row is None
        if replayed:
            row = conn.execute(
                """SELECT id, role, content, created_at FROM kdt_user_chat.messages
                   WHERE conversation_id = %s AND request_id = %s""",
                (conversation_id, body.request_id),
            ).fetchone()
            if row is None:
                raise HTTPException(503, "저장 결과를 다시 확인하세요.")
            if row["content"] != body.content:
                raise HTTPException(409, "같은 요청 ID에 다른 내용이 있습니다.")
    # with 정상 종료로 commit이 끝난 뒤 반환한다. UI는 응답 확인 후 다시 조회한다.
    return {"message": row, "replayed": replayed}


def init_db():
    # 기존 kdt_hybrid 기록은 변경하지 않는다. 별도 스키마는 소유자 없는 과거 기록과 분리한다.
    with connect_db() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS kdt_user_chat")
        conn.execute("""CREATE TABLE IF NOT EXISTS kdt_user_chat.conversations (
            id UUID PRIMARY KEY, owner_id UUID NOT NULL REFERENCES auth.users(id),
            title VARCHAR(100) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS kdt_user_chat.messages (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES kdt_user_chat.conversations(id),
            role VARCHAR(10) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'assistant')),
            content VARCHAR(1000) NOT NULL CHECK (length(trim(content)) > 0),
            request_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (conversation_id, request_id)
        )""")
    print("테이블 준비 완료")


def seed_user(email):
    # 수업용 계정 한 개의 샘플만 준비한다. 계정 생성과 비밀번호 변경은 하지 않는다.
    with connect_db() as conn:
        user = conn.execute("SELECT id FROM auth.users WHERE email = %s", (email,)).fetchone()
        if user is None:
            raise SystemExit("해당 이메일의 Auth 계정을 먼저 준비하세요.")
        for index in (1, 2):
            room_id = uuid5(NAMESPACE_URL, f"kdt-user-chat:{user['id']}:{index}")
            conn.execute(
                """INSERT INTO kdt_user_chat.conversations (id, owner_id, title)
                   VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING""",
                (room_id, user["id"], "학습 메모"),  # 같은 제목을 의도해 ID 구분을 실습한다.
            )
            conn.execute(
                """INSERT INTO kdt_user_chat.messages (conversation_id, role, content, request_id)
                   VALUES (%s, 'user', %s, %s) ON CONFLICT (conversation_id, request_id) DO NOTHING""",
                (room_id, f"샘플 {index}: 이번 수업에서 확인할 내용을 기록합니다.",
                 uuid5(NAMESPACE_URL, f"kdt-user-chat-seed:{room_id}")),
            )
    print("해당 계정의 샘플 대화 두 개 준비 완료")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="실습 DB와 계정별 샘플 준비")
    parser.add_argument("command", choices=["init", "seed"], help="테이블 준비 또는 샘플 준비")
    parser.add_argument("--email", help="seed에 사용할 기존 Auth 계정 이메일")
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_db()
        elif not args.email:
            parser.error("seed에는 --email이 필요합니다.")
        else:
            seed_user(args.email)
    except psycopg.Error:
        raise SystemExit("DB 준비 실패: 연결·권한·init 완료 여부를 확인하세요.") from None
