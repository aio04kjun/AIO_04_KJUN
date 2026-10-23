"""FastAPI + SQLite + HTML 방명록. 추가 템플릿/폼 라이브러리 없이 실행합니다."""

from contextlib import closing
from datetime import datetime, timedelta, timezone
from html import escape
import os
from pathlib import Path
import sqlite3
from string import Template
from urllib.parse import parse_qs, urlencode

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool


BASE_DIR = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
PAGE_SIZE = 6
MAX_ENTRIES = 1000
MAX_BODY_BYTES = 8192
app = FastAPI(title="작은 인사", docs_url=None, redoc_url=None, openapi_url=None)


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
    # 테이블은 이것 하나뿐입니다. 관계/ORM/별도 DB 서버를 사용하지 않습니다.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 24),
            message TEXT NOT NULL CHECK(length(message) BETWEEN 1 AND 500),
            created_at TEXT NOT NULL
        )
    """)
    connection.commit()
    return connection


def page_link(page: int, query: str) -> str:
    return "/?" + escape(urlencode({"page": page, "q": query}), quote=True) + "#notes-title"


def render_page(
    page: int = 1, query: str = "", notice: str = "", error: bool = False,
    name: str = "", message: str = "", status_code: int = 200,
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
            "SELECT id, name, message, created_at FROM entries " + where
            + " ORDER BY id DESC LIMIT ? OFFSET ?",
            (query, query, PAGE_SIZE, (page - 1) * PAGE_SIZE),
        ).fetchall()

    cards = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["created_at"])
        cards.append(
            '<article class="note"><div class="note-top">'
            f'<span class="avatar" aria-hidden="true">{escape(row["name"][0])}</span>'
            f'<strong>{escape(row["name"])}</strong>'
            f'<time datetime="{escape(row["created_at"], quote=True)}">'
            f'{timestamp:%Y.%m.%d %H:%M} · KST</time></div>'
            f'<p class="note-message">{escape(row["message"])}</p></article>'
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
        "default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
        "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", response_class=HTMLResponse)
def index(
    page: int = Query(default=1, ge=1, le=100000),
    q: str = Query(default="", max_length=50),
    saved: bool = False,
):
    return render_page(page, q.strip(), notice="마음을 남겨주셔서 고마워요. 인사가 등록되었습니다." if saved else "")


@app.get("/static/style.css", include_in_schema=False)
def stylesheet():
    return FileResponse(BASE_DIR / "static/style.css", media_type="text/css")


@app.get("/static/validation.js", include_in_schema=False)
def validation_script():
    return FileResponse(BASE_DIR / "static/validation.js", media_type="text/javascript")


def save_entry(entry: EntryIn) -> bool:
    with closing(connect_db()) as connection:
        # 개수 확인과 INSERT를 한 트랜잭션에 넣어 동시 요청에서도 상한을 지킵니다.
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT count(*) FROM entries").fetchone()[0] >= MAX_ENTRIES:
                return False
            connection.execute(
                "INSERT INTO entries (name, message, created_at) VALUES (?, ?, ?)",
                (entry.name, entry.message, datetime.now(KST).isoformat(timespec="seconds")),
            )
    return True


@app.post("/entries", response_class=HTMLResponse)
async def create_entry(request: Request):
    async def invalid(text: str, status_code: int, name: str = "", message: str = ""):
        return await run_in_threadpool(
            render_page, notice=text, error=True, name=name, message=message, status_code=status_code
        )

    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and origin != str(request.base_url).rstrip("/")
    ):
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

    if not await run_in_threadpool(save_entry, entry):
        return await invalid("방명록의 저장 한도에 도달했습니다. 운영자에게 문의해주세요.", 409, entry.name, entry.message)
    # POST 후 GET으로 이동하여 새로고침 시 중복 제출을 방지합니다.
    return RedirectResponse("/?saved=true#write", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
