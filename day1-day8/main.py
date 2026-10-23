"""FastAPI + SQLite + HTML 방명록. 추가 템플릿/폼 라이브러리 없이 실행합니다."""

from contextlib import closing
from datetime import datetime, timedelta, timezone
from html import escape
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import secrets
from string import Template
from urllib.parse import parse_qs, urlencode

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool


BASE_DIR = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
PAGE_SIZE = 6
MAX_ENTRIES = 1000
MAX_BODY_BYTES = 8192
MAX_LIKES = 1000
MAX_REPLIES = 30
app = FastAPI(title="작은 인사", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
OWNER_COOKIE = "guestbook_owner"


def owner_token(request: Request) -> str:
    token = request.cookies.get(OWNER_COOKIE, "")
    return token if len(token) == 43 and all(c.isascii() and (c.isalnum() or c in "-_") for c in token) else ""


def owner_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest() if token else ""


class EntryIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=24)
    message: str = Field(min_length=1, max_length=500)


def database_path() -> Path:
    """상대 경로도 실행 위치 대신 프로젝트 폴더를 기준으로 해석합니다."""
    configured = Path(os.environ.get("GUESTBOOK_DB", "data/guestbook.db"))
    return configured if configured.is_absolute() else BASE_DIR / configured


def connect_db() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("BEGIN IMMEDIATE")
    # 테이블은 이것 하나뿐입니다. 관계/ORM/별도 DB 서버를 사용하지 않습니다.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 24),
            message TEXT NOT NULL CHECK(length(message) BETWEEN 1 AND 500),
            created_at TEXT NOT NULL
        )
    """)
    # 기존 DB의 글은 지우지 않고 같은 테이블에 작성자 식별 열만 추가합니다.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(entries)")}
    if "owner_hash" not in columns:
        connection.execute("ALTER TABLE entries ADD COLUMN owner_hash TEXT NOT NULL DEFAULT ''")
    # 좋아요와 답글은 글의 JSON 열에 보관해 테이블 하나를 유지합니다.
    for column in ("likes_json", "replies_json"):
        if column not in columns:
            connection.execute(f"ALTER TABLE entries ADD COLUMN {column} TEXT NOT NULL DEFAULT '[]'")
    connection.commit()
    return connection


def page_link(page: int, query: str) -> str:
    return "/?" + escape(urlencode({"page": page, "q": query}), quote=True) + "#notes-title"


def render_page(
    page: int = 1, query: str = "", notice: str = "", error: bool = False,
    name: str = "", message: str = "", status_code: int = 200,
    token: str = "", editing_id: int | None = None,
    open_thread: int | None = None, reply_draft: dict | None = None,
) -> HTMLResponse:
    # instr은 검색어의 %와 _도 보통 글자로 취급하며 SQL 매개변수로 전달합니다.
    with closing(connect_db()) as connection:
        total = connection.execute("SELECT count(*) FROM entries").fetchone()[0]
        where = "WHERE instr(lower(name), lower(?)) > 0 OR instr(lower(message), lower(?)) > 0"
        matched = connection.execute(
            "SELECT count(*) FROM entries " + where, (query, query)
        ).fetchone()[0]
        pages = max(1, (matched + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages)
        rows = connection.execute(
            "SELECT * FROM entries " + where
            + " ORDER BY id DESC LIMIT ? OFFSET ?",
            (query, query, PAGE_SIZE, (page - 1) * PAGE_SIZE),
        ).fetchall()

    cards = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["created_at"])
        actions = ""
        if token and row["owner_hash"] == owner_hash(token):
            actions = (
                '<div class="note-actions"><span class="my-note">MY SIGNAL</span>'
                f'<a href="/entries/{row["id"]}/edit#write">수정</a>'
                '<details class="delete-confirm"><summary>삭제</summary>'
                f'<form method="post" action="/entries/{row["id"]}/delete">'
                '<p>이 인사를 삭제할까요?<br>달린 답글과 좋아요도 함께 삭제됩니다.</p>'
                '<button type="submit">삭제 확인</button></form></details></div>'
            )
        cards.append(
            f'<article class="note" id="note-{row["id"]}"><div class="note-top">'
            f'<span class="avatar" aria-hidden="true">{escape(row["name"][0])}</span>'
            f'<strong>{escape(row["name"])}</strong>'
            f'<time datetime="{escape(row["created_at"], quote=True)}">'
            f'{timestamp:%Y.%m.%d %H:%M} · KST</time></div>'
            f'<p class="note-message">{escape(row["message"])}</p>{actions}'
            + render_social(row, token, page, query, open_thread, reply_draft) + '</article>'
        )
    if not cards:
        title = "검색된 이야기가 없어요" if query else "첫 번째 마음을 기다리고 있어요"
        description = "다른 이름이나 이야기로 다시 찾아보세요." if query else "이 공간의 첫 인사를 남겨주세요."
        cards.append(
            '<div class="empty"><span class="empty-symbol" aria-hidden="true">✳</span>'
            f'<h3>{title}</h3><p>{description}</p><a href="#write">인사 남기러 가기 ↗</a></div>'
        )

    navigation = ""
    if pages > 1:
        previous = f'<a href="{page_link(page - 1, query)}" rel="prev">← 이전</a>' if page > 1 else ""
        following = f'<a href="{page_link(page + 1, query)}" rel="next">다음 →</a>' if page < pages else ""
        navigation = f'<nav class="pagination" aria-label="방명록 페이지">{previous}<span>{page} / {pages}</span>{following}</nav>'

    notice_html = ""
    if notice:
        notice_class = "notice error" if error else "notice"
        notice_html = f'<p class="{notice_class}" role="{"alert" if error else "status"}">{escape(notice)}</p>'
    values = {
        "total": str(total), "query": escape(query, quote=True),
        "name": escape(name, quote=True), "message": escape(message),
        "notice": notice_html, "entries": "".join(cards), "pagination": navigation,
        "form_action": f"/entries/{editing_id}/edit" if editing_id else "/entries",
        "form_title": "당신의 신호를 다듬어보세요" if editing_id else "우주에 인사를 남겨보세요",
        "submit_label": "수정한 마음 저장하기" if editing_id else "나의 신호 보내기",
        "cancel_edit": '<a class="cancel-edit" href="/#write">수정 취소</a>' if editing_id else "",
        "clear_search": '<a class="clear-search" href="/#notes-title">초기화</a>' if query else "",
        "search_summary": f'<p class="search-summary">“{escape(query)}” 검색 결과 {matched}개</p>' if query else "",
    }
    # Template은 딱 한 번만 치환하여 사용자 글 속의 {{...}}를 다시 처리하지 않습니다.
    source = (BASE_DIR / "templates/index.html").read_text(encoding="utf-8")
    for key in values:
        source = source.replace("{{" + key + "}}", "${" + key + "}")
    html = Template(source).substitute(values)
    return HTMLResponse(html, status_code=status_code)


@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    page: int = Query(default=1, ge=1, le=100000),
    q: str = Query(default="", max_length=50),
    saved: bool = False,
    updated: bool = False,
    deleted: bool = False,
    thread: int | None = Query(default=None, ge=1),
):
    notice = "마음을 남겨주셔서 고마워요. 인사가 등록되었습니다." if saved else ""
    if updated:
        notice = "당신의 인사를 수정했습니다. 새로운 마음이 전해졌어요."
    if deleted:
        notice = "인사를 삭제했습니다. 다음 이야기도 기다릴게요."
    return render_page(page, q.strip(), notice=notice, token=owner_token(request), open_thread=thread)


def save_entry(entry: EntryIn, token: str = "") -> bool:
    with closing(connect_db()) as connection:
        # 개수 확인과 INSERT를 한 트랜잭션에 넣어 동시 요청에서도 상한을 지킵니다.
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT count(*) FROM entries").fetchone()[0] >= MAX_ENTRIES:
                return False
            connection.execute(
                "INSERT INTO entries (name, message, created_at, owner_hash) VALUES (?, ?, ?, ?)",
                (entry.name, entry.message, datetime.now(KST).isoformat(timespec="seconds"), owner_hash(token)),
            )
    return True


@app.post("/entries", response_class=HTMLResponse)
async def create_entry(request: Request):
    return await submit_entry(request)


def owned_entry(entry_id: int, token: str):
    with closing(connect_db()) as connection:
        row = connection.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "인사를 찾을 수 없습니다.")
    if not token or not row["owner_hash"] or not secrets.compare_digest(row["owner_hash"], owner_hash(token)):
        raise HTTPException(403, "작성한 브라우저에서만 수정·삭제할 수 있습니다.")
    return row


@app.get("/entries/{entry_id}/edit", response_class=HTMLResponse)
def edit_page(request: Request, entry_id: int):
    token = owner_token(request)
    row = owned_entry(entry_id, token)
    return render_page(name=row["name"], message=row["message"], token=token, editing_id=entry_id)


@app.post("/entries/{entry_id}/edit", response_class=HTMLResponse)
async def edit_entry(request: Request, entry_id: int):
    return await submit_entry(request, entry_id)


def allowed_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    return request.headers.get("sec-fetch-site") != "cross-site" and (
        not origin or origin == str(request.base_url).rstrip("/")
    )


@app.post("/entries/{entry_id}/delete")
def delete_entry(request: Request, entry_id: int):
    if not allowed_origin(request):
        raise HTTPException(403, "외부 사이트에서는 삭제할 수 없습니다.")
    token = owner_token(request)
    owned_entry(entry_id, token)
    with closing(connect_db()) as connection, connection:
        cursor = connection.execute("DELETE FROM entries WHERE id = ? AND owner_hash = ?", (entry_id, owner_hash(token)))
        if cursor.rowcount == 0:
            raise HTTPException(404, "인사를 찾을 수 없습니다.")
    return RedirectResponse("/?deleted=true#notes-title", status_code=303)


async def submit_entry(request: Request, editing_id: int | None = None):
    token = owner_token(request)
    if editing_id is not None:
        await run_in_threadpool(owned_entry, editing_id, token)

    async def invalid(text: str, status_code: int, name: str = "", message: str = ""):
        return await run_in_threadpool(
            render_page, notice=text, error=True, name=name, message=message, status_code=status_code,
            token=token, editing_id=editing_id,
        )

    if not allowed_origin(request):
        return await invalid("외부 사이트에서는 글을 등록할 수 없습니다.", 403)
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/x-www-form-urlencoded":
        return await invalid("방명록의 입력 양식으로 작성해주세요.", 415)

    # multipart 패키지 없이 HTML 기본 폼 형식만 처리합니다. 큰 본문은 읽는 중 중단합니다.
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            return await invalid("입력한 내용이 너무 큽니다. 이야기는 500자 이내로 작성해주세요.", 413)
        body.extend(chunk)
    fields = {}
    try:
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=2, errors="strict")
        if any(len(values) != 1 for values in fields.values()):
            raise ValueError("중복 필드")
        entry = EntryIn.model_validate({key: values[0] for key, values in fields.items()})
    except (ValueError, ValidationError):
        # 검증 실패 때도 적어둔 내용을 보존합니다. HTML에 넣기 전 escape합니다.
        return await invalid(
            "이름은 1–24자, 이야기는 1–500자로 입력해주세요. 공백만 입력할 수 없습니다.", 422,
            fields.get("name", [""])[0][:24], fields.get("message", [""])[0][:500],
        )

    if editing_id is not None:
        await run_in_threadpool(update_entry, editing_id, entry, token)
        return RedirectResponse("/?updated=true#write", status_code=303)

    token = token or secrets.token_urlsafe(32)
    if not await run_in_threadpool(save_entry, entry, token):
        return await invalid("방명록의 저장 한도에 도달했습니다. 운영자에게 문의해주세요.", 409, entry.name, entry.message)
    # POST 후 GET으로 이동하여 새로고침 시 중복 제출을 방지합니다.
    response = RedirectResponse("/?saved=true#write", status_code=303)
    response.set_cookie(OWNER_COOKIE, token, max_age=31536000, httponly=True, secure=request.url.scheme == "https", samesite="lax")
    return response


def update_entry(entry_id: int, entry: EntryIn, token: str):
    with closing(connect_db()) as connection, connection:
        cursor = connection.execute(
            "UPDATE entries SET name = ?, message = ? WHERE id = ? AND owner_hash = ?",
            (entry.name, entry.message, entry_id, owner_hash(token)),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "인사를 찾을 수 없습니다.")


def social_action(entry_id: int, suffix: str, page: int, query: str) -> str:
    return escape(f"/entries/{entry_id}/{suffix}?" + urlencode({"page": page, "q": query}), quote=True)


def thread_location(entry_id: int, page: int, query: str) -> str:
    return "/?" + urlencode({"page": page, "q": query, "thread": entry_id}) + f"#note-{entry_id}"


def render_reply_form(action: str, prefix: str, name: str = "", message: str = "", editing: bool = False, error: str = "") -> str:
    error_html = f'<p class="reply-error" role="alert">{escape(error)}</p>' if error else ""
    fields = []
    for field, label, hint, limit, value in (
        ("name", "이름", "어떻게 불러드릴까요?", 24, name),
        ("message", "답글", "이 마음에 작은 답장을 남겨주세요.", 500, message),
    ):
        field_id = f"{prefix}-{field}"
        attributes = f'id="{field_id}" name="{field}" maxlength="{limit}" required aria-describedby="{field_id}-help" placeholder="{hint}"'
        control = (f'<input {attributes} autocomplete="nickname" value="{escape(value, quote=True)}">' if field == "name"
                   else f'<textarea {attributes} rows="3">{escape(value)}</textarea>')
        fields.append(
            f'<div class="field"><label for="{field_id}">{label}<span>필수</span></label>{control}'
            f'<div id="{field_id}-error" class="validation-bubble" role="alert" hidden>'
            f'<span class="validation-icon" aria-hidden="true">✧</span><div><strong>{label}을 입력해주세요</strong>'
            '<p>공백 대신 한 글자 이상 적어주세요.</p></div></div>'
            f'<small id="{field_id}-help">1–{limit}자</small></div>'
        )
    label = "답글 수정 저장" if editing else "답글 보내기"
    return (
        f'<form class="reply-form" data-note-form method="post" action="{action}">{error_html}'
        + "".join(fields)
        + '<p class="reply-privacy">답글은 공개되며, 작성한 브라우저에서 수정·삭제할 수 있어요.</p>'
        + f'<button class="reply-submit" type="submit">{label} <span aria-hidden="true">↗</span></button></form>'
    )


def render_social(row, token: str, page: int, query: str, open_thread: int | None, draft: dict | None) -> str:
    entry_id = row["id"]
    digest = owner_hash(token)
    likes = json.loads(row["likes_json"])
    replies = json.loads(row["replies_json"])
    liked = bool(token and digest in likes)
    is_draft = bool(draft and draft["entry_id"] == entry_id)
    pressed = "true" if liked else "false"
    target = "false" if liked else "true"
    parts = [
        '<div class="note-social">'
        f'<form class="like-form" method="post" action="{social_action(entry_id, "like", page, query)}">'
        f'<input type="hidden" name="liked" value="{target}">'
        f'<button class="like-button" type="submit" aria-pressed="{pressed}">'
        f'<span class="heart" data-like-icon aria-hidden="true">{"♥" if liked else "♡"}</span>'
        f'<span>좋아요</span><span class="like-count" data-like-count>{len(likes)}</span></button></form>'
        '<p class="social-feedback" role="status" hidden></p></div>'
        f'<details class="reply-thread" id="thread-{entry_id}"{" open" if open_thread == entry_id or is_draft else ""}>'
        f'<summary><span aria-hidden="true">↳</span> 답글 <span class="reply-count">{len(replies)}</span><span class="reply-chevron" aria-hidden="true">⌄</span></summary>'
        '<div class="reply-content"><div class="reply-list">'
    ]
    for reply in replies:
        reply_id = reply["id"]
        timestamp = datetime.fromisoformat(reply["created_at"])
        controls = ""
        if token and reply["owner_hash"] == digest:
            edit_draft = is_draft and draft.get("reply_id") == reply_id
            edit_form = render_reply_form(
                social_action(entry_id, f"replies/{reply_id}/edit", page, query), f"edit-{reply_id}",
                draft["name"] if edit_draft else reply["name"],
                draft["message"] if edit_draft else reply["message"], editing=True,
                error=draft["error"] if edit_draft else "",
            )
            controls = (
                '<div class="reply-actions">'
                f'<details class="reply-edit"{" open" if edit_draft else ""}><summary>수정</summary>{edit_form}</details>'
                '<details class="delete-confirm"><summary>삭제</summary>'
                f'<form method="post" action="{social_action(entry_id, f"replies/{reply_id}/delete", page, query)}">'
                '<p>이 답글을 삭제할까요?<br>삭제한 답글은 되돌릴 수 없어요.</p>'
                '<button type="submit">답글 삭제 확인</button></form></details></div>'
            )
        parts.append(
            f'<article class="reply" id="reply-{reply_id}"><div class="reply-top">'
            f'<strong>{escape(reply["name"])}</strong><time datetime="{escape(reply["created_at"], quote=True)}">'
            f'{timestamp:%Y.%m.%d %H:%M} · KST</time></div>'
            f'<p class="reply-message">{escape(reply["message"])}</p>{controls}</article>'
        )
    parts.append('</div>')
    if not replies:
        parts.append('<p class="reply-empty">아직 도착한 답장이 없어요. 첫 답장을 보내보세요.</p>')
    if len(replies) < MAX_REPLIES:
        new_draft = is_draft and not draft.get("reply_id")
        parts.append(render_reply_form(
            social_action(entry_id, "replies", page, query), f"new-{entry_id}",
            draft["name"] if new_draft else "", draft["message"] if new_draft else "",
            error=draft["error"] if new_draft else "",
        ))
    else:
        parts.append('<p class="reply-empty">이 글에 도착할 수 있는 답글이 모두 찼어요. (최대 30개)</p>')
    parts.append('</div></details>')
    return "".join(parts)


async def social_fields(request: Request) -> dict[str, str]:
    """추가 폼도 기본 URL 인코딩과 기존 본문 상한만 사용합니다."""
    if not allowed_origin(request):
        raise HTTPException(403, "외부 사이트에서는 요청할 수 없습니다.")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/x-www-form-urlencoded":
        raise HTTPException(415, "화면의 입력 양식으로 작성해주세요.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "입력한 내용이 너무 큽니다.")
        body.extend(chunk)
    try:
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=2, errors="strict")
        if any(len(values) != 1 for values in fields.values()):
            raise ValueError("중복 필드")
        return {key: values[0] for key, values in fields.items()}
    except ValueError as error:
        raise HTTPException(422, "입력 양식을 확인해주세요.") from error


def set_owner_cookie(response, request: Request, token: str):
    response.set_cookie(OWNER_COOKIE, token, max_age=31536000, httponly=True,
                        secure=request.url.scheme == "https", samesite="lax")
    return response


def social_mutation(entry_id: int, token: str, action: str, entry: EntryIn | None = None,
                    reply_id: str | None = None, desired_like: bool = False) -> dict:
    """조회와 변경을 같은 트랜잭션으로 처리해 좋아요·답글 갱신 유실을 막습니다."""
    with closing(connect_db()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "인사를 찾을 수 없습니다.")
        digest = owner_hash(token)
        if action == "like":
            likes = json.loads(row["likes_json"])
            if desired_like and digest not in likes:
                if len(likes) >= MAX_LIKES:
                    raise HTTPException(409, "이 글의 좋아요 한도에 도달했습니다.")
                likes.append(digest)
            elif not desired_like and digest in likes:
                likes.remove(digest)
            connection.execute("UPDATE entries SET likes_json = ? WHERE id = ?", (json.dumps(likes), entry_id))
            return {"liked": desired_like, "count": len(likes)}

        replies = json.loads(row["replies_json"])
        if action == "reply":
            if len(replies) >= MAX_REPLIES:
                raise HTTPException(409, "답글은 글 하나당 최대 30개까지 남길 수 있습니다.")
            replies.append({"id": secrets.token_hex(12), "name": entry.name, "message": entry.message,
                            "owner_hash": digest, "created_at": datetime.now(KST).isoformat(timespec="seconds")})
        else:
            reply = next((item for item in replies if item["id"] == reply_id), None)
            if reply is None:
                raise HTTPException(404, "답글을 찾을 수 없습니다.")
            if not token or not secrets.compare_digest(reply["owner_hash"], digest):
                raise HTTPException(403, "답글을 작성한 브라우저에서만 수정·삭제할 수 있습니다.")
            if action == "edit":
                reply.update(name=entry.name, message=entry.message)
            elif action == "delete":
                replies.remove(reply)
        connection.execute("UPDATE entries SET replies_json = ? WHERE id = ?",
                           (json.dumps(replies, ensure_ascii=False), entry_id))
    return {}


@app.post("/entries/{entry_id}/like")
async def like_entry(request: Request, entry_id: int,
                     page: int = Query(default=1, ge=1, le=100000), q: str = Query(default="", max_length=50)):
    fields = await social_fields(request)
    if set(fields) != {"liked"} or fields["liked"] not in ("true", "false"):
        raise HTTPException(422, "좋아요 상태를 확인해주세요.")
    token = owner_token(request) or secrets.token_urlsafe(32)
    result = await run_in_threadpool(social_mutation, entry_id, token, "like", desired_like=fields["liked"] == "true")
    response = (JSONResponse(result) if "application/json" in request.headers.get("accept", "")
                else RedirectResponse(thread_location(entry_id, page, q), status_code=303))
    return set_owner_cookie(response, request, token)


async def submit_reply(request: Request, entry_id: int, page: int, query: str, reply_id: str | None = None):
    fields = await social_fields(request)
    token = owner_token(request)
    await run_in_threadpool(check_reply_target, entry_id, token, reply_id)
    try:
        entry = EntryIn.model_validate(fields)
    except ValidationError:
        draft = {"entry_id": entry_id, "reply_id": reply_id, "name": fields.get("name", "")[:24],
                 "message": fields.get("message", "")[:500],
                 "error": "이름은 1–24자, 답글은 1–500자로 입력해주세요. 공백만 입력할 수 없습니다."}
        return await run_in_threadpool(render_page, page=page, query=query, token=token,
                                       open_thread=entry_id, reply_draft=draft, status_code=422)
    token = token or secrets.token_urlsafe(32)
    await run_in_threadpool(social_mutation, entry_id, token, "edit" if reply_id else "reply", entry, reply_id)
    response = RedirectResponse(thread_location(entry_id, page, query), status_code=303)
    return set_owner_cookie(response, request, token)


def check_reply_target(entry_id: int, token: str, reply_id: str | None):
    with closing(connect_db()) as connection:
        row = connection.execute("SELECT replies_json FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "인사를 찾을 수 없습니다.")
    if reply_id is not None:
        reply = next((item for item in json.loads(row["replies_json"]) if item["id"] == reply_id), None)
        if reply is None:
            raise HTTPException(404, "답글을 찾을 수 없습니다.")
        if not token or not secrets.compare_digest(reply["owner_hash"], owner_hash(token)):
            raise HTTPException(403, "답글을 작성한 브라우저에서만 수정·삭제할 수 있습니다.")


@app.post("/entries/{entry_id}/replies")
async def create_reply(request: Request, entry_id: int,
                       page: int = Query(default=1, ge=1, le=100000), q: str = Query(default="", max_length=50)):
    return await submit_reply(request, entry_id, page, q)


@app.post("/entries/{entry_id}/replies/{reply_id}/edit")
async def edit_reply(request: Request, entry_id: int, reply_id: str,
                     page: int = Query(default=1, ge=1, le=100000), q: str = Query(default="", max_length=50)):
    return await submit_reply(request, entry_id, page, q, reply_id)


@app.post("/entries/{entry_id}/replies/{reply_id}/delete")
def delete_reply(request: Request, entry_id: int, reply_id: str,
                 page: int = Query(default=1, ge=1, le=100000), q: str = Query(default="", max_length=50)):
    if not allowed_origin(request):
        raise HTTPException(403, "외부 사이트에서는 삭제할 수 없습니다.")
    social_mutation(entry_id, owner_token(request), "delete", reply_id=reply_id)
    return RedirectResponse(thread_location(entry_id, page, q), status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
