"""Supabase Auth로 확인한 사용자만 Redis 컨텍스트를 사용한다."""
import argparse
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import hashlib
import os
import time
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import APIConnectionError, APIStatusError, OpenAI
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from redis import Redis, RedisError
from supabase import AuthApiError, AuthRetryableError, create_client
from supabase.client import ClientOptions

load_dotenv(".env", override=False, interpolate=False)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
REDIS_URL = os.getenv("REDIS_URL", "").strip()
TTL_TEXT = os.getenv("SESSION_TTL_SECONDS", "").strip()
for name, value in {"SUPABASE_URL": SUPABASE_URL, "SUPABASE_PUBLISHABLE_KEY": SUPABASE_KEY,
                    "REDIS_URL": REDIS_URL, "SESSION_TTL_SECONDS": TTL_TEXT}.items():
    if not value:
        raise RuntimeError(f".env의 {name} 값을 입력하세요.")
if not SUPABASE_URL.startswith("https://"):
    raise RuntimeError("SUPABASE_URL 주소를 확인하세요.")
if not REDIS_URL.startswith(("redis://", "rediss://")) or "?" in REDIS_URL:
    raise RuntimeError("REDIS_URL은 옵션 없는 Redis URI를 사용하세요.")
try:
    SESSION_TTL_SECONDS = int(TTL_TEXT)
except ValueError:
    raise RuntimeError("SESSION_TTL_SECONDS는 양의 정수입니다.") from None
if SESSION_TTL_SECONDS <= 0:
    raise RuntimeError("SESSION_TTL_SECONDS는 양의 정수입니다.")

app = FastAPI(title="사용자별 멀티턴 대화")
bearer = HTTPBearer(auto_error=False)


@app.exception_handler(RedisError)
async def redis_error(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "Redis 연결을 확인하세요."})

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
for name, value in {"LLM_BASE_URL": LLM_BASE_URL, "LLM_MODEL": LLM_MODEL,
                    "LLM_API_KEY": LLM_API_KEY}.items():
    if not value.strip():
        raise RuntimeError(f".env의 {name} 값을 입력하세요.")
if not LLM_BASE_URL.startswith(("http://", "https://")):
    raise RuntimeError("LLM_BASE_URL 주소를 확인하세요.")

class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=1, max_length=254)
    # 비밀번호는 strip하지 않고, 검증 오류와 repr에 원문이 나오지 않도록 한다.
    password: SecretStr = Field(min_length=1, max_length=1024)


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):
    # 비밀번호 등 원본 input 값을 응답에 포함하지 않는다.
    errors = [{"loc": e["loc"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


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

SYSTEM_MESSAGE = {"role": "system", "content": "한국어로 두 문장 안에서 답하세요. 대화에 나온 정보를 사용하고 모르는 개인 정보는 모른다고 말하세요."}


def generate_answer(messages):
    # 모델 키는 백엔드에서만 읽고 브라우저로 전달하지 않는다.
    try:
        with OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY,
                    timeout=120.0, max_retries=0) as client:
            result = client.chat.completions.create(
                model=LLM_MODEL, messages=messages,
            )
    except (APIConnectionError, APIStatusError):
        raise HTTPException(502, "모델 API 연결과 모델 이름을 확인하세요.") from None
    answer = result.choices[0].message.content if result.choices else None
    if not answer or not answer.strip():
        raise HTTPException(502, "모델에서 비어 있는 답변을 받았습니다.")
    return answer.strip()[:1000]  # 이 실습의 답변 보관 길이는 최대 1000자다.

def build_messages(history, question):
    current = [{"role": "user", "content": question}]
    return [SYSTEM_MESSAGE] + history[-4:] + current

DB_URL = os.getenv("SUPABASE_DB_URL", "")
if not DB_URL.strip():
    raise RuntimeError("SUPABASE_DB_URL을 입력하세요.")


@app.exception_handler(psycopg.Error)
async def database_error(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "DB 연결과 init 완료 여부를 확인하세요."})


def connect_db():
    return psycopg.connect(DB_URL, connect_timeout=5, sslmode="require", row_factory=dict_row)


class ConversationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=100)


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    conversation_id: UUID
    request_id: UUID
    question: str = Field(min_length=1, max_length=1000)


def require_room(conn, conversation_id, user_id, lock=False):
    sql = "SELECT id, title FROM kdt_multiturn.conversations WHERE id = %s AND owner_id = %s"
    if lock:
        sql += " FOR UPDATE"
    room = conn.execute(sql, (conversation_id, UUID(user_id))).fetchone()
    if room is None:
        raise HTTPException(404, "자기 계정의 대화를 선택하세요.")
    return room


def read_history(conn, conversation_id):
    rows = conn.execute(
        "SELECT question, answer FROM kdt_multiturn.turns WHERE conversation_id = %s ORDER BY id",
        (conversation_id,),
    ).fetchall()
    history = []
    for row in rows:
        history.extend([
            {"role": "user", "content": row["question"]},
            {"role": "assistant", "content": row["answer"]},
        ])
    return history


@app.get("/conversations")
def list_conversations(user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        return conn.execute(
            "SELECT id, title FROM kdt_multiturn.conversations WHERE owner_id = %s ORDER BY created_at, id",
            (UUID(user["id"]),),
        ).fetchall()


@app.post("/conversations")
def create_conversation(body: ConversationInput, user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        room = conn.execute(
            "INSERT INTO kdt_multiturn.conversations (id, owner_id, title) VALUES (%s, %s, %s) RETURNING id, title",
            (uuid4(), UUID(user["id"]), body.title),
        ).fetchone()
    return room


@app.get("/conversations/{conversation_id}/messages")
def history(conversation_id: UUID, user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        require_room(conn, conversation_id, user["id"])
        return read_history(conn, conversation_id)


@app.post("/chat")
def chat(body: ChatInput, user: Annotated[dict, Depends(require_user)]):
    with connect_db() as conn:
        # 같은 대화의 요청은 차례로 처리하고, 소유권도 서버에서 확인한다.
        require_room(conn, body.conversation_id, user["id"], lock=True)
        previous = conn.execute(
            "SELECT question, answer, context_json FROM kdt_multiturn.turns WHERE conversation_id = %s AND request_id = %s",
            (body.conversation_id, body.request_id),
        ).fetchone()
        if previous:
            if previous["question"] != body.question:
                raise HTTPException(409, "같은 요청 번호의 질문이 다릅니다.")
            return {"answer": previous["answer"], "context_messages": previous["context_json"],
                    "previous_count": len(previous["context_json"]) - 2, "replayed": True}
        history = read_history(conn, body.conversation_id)
        messages = build_messages(history, body.question)
        answer = generate_answer(messages)
        # API 실패 시 여기까지 오지 않는다. 성공한 질문과 답변만 한 행으로 저장한다.
        conn.execute(
            """INSERT INTO kdt_multiturn.turns
               (conversation_id, request_id, question, answer, context_json)
               VALUES (%s, %s, %s, %s, %s)""",
            (body.conversation_id, body.request_id, body.question, answer, Jsonb(messages)),
        )
    return {"answer": answer, "context_messages": messages,
            "previous_count": len(messages) - 2, "replayed": False}


def init_db():
    with connect_db() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS kdt_multiturn")
        conn.execute("""CREATE TABLE IF NOT EXISTS kdt_multiturn.conversations (
            id UUID PRIMARY KEY,
            owner_id UUID NOT NULL REFERENCES auth.users(id),
            title VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS kdt_multiturn.turns (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES kdt_multiturn.conversations(id),
            request_id UUID NOT NULL,
            question VARCHAR(1000) NOT NULL,
            answer VARCHAR(1000) NOT NULL,
            context_json JSONB NOT NULL,
            UNIQUE(conversation_id, request_id)
        )""")
    print("멀티턴 테이블 준비 완료")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init"])
    parser.parse_args()
    init_db()
