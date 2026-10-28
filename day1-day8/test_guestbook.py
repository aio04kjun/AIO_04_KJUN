"""수업의 pytest/TestClient 패턴. 실제 DB와 분리된 임시 SQLite를 사용합니다."""
import sqlite3
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    pytest.skip("SQLite 전용 이전 테스트입니다. Supabase 검증은 verify_supabase.py를 실행하세요.")
    monkeypatch.setenv("GUESTBOOK_DB", str(tmp_path / "guestbook.db"))
    with TestClient(main.app) as test_client:
        yield test_client


def test_empty_page_and_css(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert "첫 번째 마음을 기다리고 있어요" in response.text
    assert '<script src="/static/validation.js" defer></script>' in response.text
    assert "{{" not in response.text
    assert client.get("/static/style.css").status_code == 200


def test_post_redirect_persist_and_single_table(client):
    response = client.post("/entries", data={"name": "  방문자  ", "message": "안녕하세요\n반가워요!"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/?saved=true#write"
    with sqlite3.connect(main.database_path()) as connection:
        assert connection.execute("SELECT name, message FROM entries").fetchone() == ("방문자", "안녕하세요\n반가워요!")
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("entries",)]
    # 새 앱 클라이언트에서도 같은 파일을 읽으며, GET 재요청은 글을 추가하지 않습니다.
    with TestClient(main.app) as second:
        assert "안녕하세요\n반가워요!" in second.get("/").text
        assert "인사가 등록되었습니다" in second.get("/?saved=true").text
    assert client.get("/").text.count('<article class="note"') == 1


@pytest.mark.parametrize("data", [
    {"name": "", "message": "안녕"}, {"name": " \t", "message": "안녕"},
    {"name": "가" * 25, "message": "안녕"}, {"name": "손님", "message": " \n "},
    {"name": "손님", "message": "가" * 501}, {"name": "손님"},
    {"name": "손님", "message": "안녕", "extra": "no"},
])
def test_invalid_input_does_not_save(client, data):
    response = client.post("/entries", data=data)
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert "첫 번째 마음을 기다리고 있어요" in client.get("/").text


def test_maximum_lengths(client):
    response = client.post("/entries", data={"name": "이" * 24, "message": "😀" * 500})
    assert response.status_code == 200
    assert "😀" * 500 in response.text


def test_html_and_template_injection_are_text(client):
    message = '<script>alert(1)</script> {{pagination}} ${name} & 한글'
    client.post("/entries", data={"name": '<img src=x>', "message": message})
    html = client.get("/").text
    assert "<script>" not in html and "<img src=x>" not in html
    assert "&lt;script&gt;" in html and "&lt;img src=x&gt;" in html
    assert "{{pagination}} ${name} &amp; 한글" in html


def test_search_literal_sql_and_pagination(client):
    for number in range(8):
        client.post("/entries", data={"name": f"손님{number}", "message": f"인사{number}"})
    first = client.get("/").text
    assert first.count('<article class="note"') == 6
    assert first.index("인사7") < first.index("인사2")
    second = client.get("/?page=2").text
    assert second.count('<article class="note"') == 2
    assert "인사0" in second
    assert 'rel="prev"' in second
    result = client.get("/", params={"q": "손님3"}).text
    assert result.count('<article class="note"') == 1
    assert "인사3" in result
    for term in ["%", "_", "' OR 1=1 --"]:
        assert "검색된 이야기가 없어요" in client.get("/", params={"q": term}).text
    assert client.get("/?page=0").status_code == 422
    assert client.get("/", params={"q": "가" * 51}).status_code == 422


def test_search_pagination_keeps_query(client):
    for number in range(7):
        client.post("/entries", data={"name": "찾기", "message": str(number)})
    response = client.get("/", params={"q": "찾기"})
    assert "page=2&amp;q=" in response.text
    assert "검색 결과 7개" in response.text


def test_request_limits_and_origin(client):
    data = {"name": "손님", "message": "인사"}
    assert client.post("/entries", json=data).status_code == 415
    assert client.post("/entries", data=data, headers={"origin": "https://other.example"}).status_code == 403
    assert client.post("/entries", data=data, headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert client.post("/entries", data=data, headers={"origin": "http://testserver"}).status_code == 200
    headers = {"content-type": "application/x-www-form-urlencoded"}
    assert client.post("/entries", content="x=" + "x" * 8192, headers=headers).status_code == 413
    assert client.post("/entries", content="name=a&name=b&message=c", headers=headers).status_code == 422
    assert client.post("/entries", content=b"name=%FF&message=a", headers=headers).status_code == 422


def test_storage_cap_and_preserve_invalid_input(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_ENTRIES", 1)
    client.post("/entries", data={"name": "첫 손님", "message": "안녕"})
    response = client.post("/entries", data={"name": "다음 손님", "message": "남길 이야기"})
    assert response.status_code == 409
    assert "저장 한도" in response.text
    assert 'value="다음 손님"' in response.text
    assert ">남길 이야기</textarea>" in response.text
    response = client.post("/entries", data={"name": "", "message": "보존할 글"})
    assert ">보존할 글</textarea>" in response.text


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["cache-control"] == "no-store"
    assert "form-action 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_owner_can_edit_and_delete(client):
    response = client.post("/entries", data={"name": "별손님", "message": "첫 번째 신호"}, follow_redirects=False)
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    token = client.cookies.get(main.OWNER_COOKIE)
    assert len(token) == 43
    with sqlite3.connect(main.database_path()) as connection:
        stored = connection.execute("SELECT owner_hash, created_at FROM entries WHERE id=1").fetchone()
    assert stored[0] != token and len(stored[0]) == 64
    assert f'href="/entries/1/edit#write"' in client.get("/").text
    editor = client.get("/entries/1/edit")
    assert editor.status_code == 200
    assert 'action="/entries/1/edit"' in editor.text
    assert 'value="별손님"' in editor.text
    assert ">첫 번째 신호</textarea>" in editor.text
    invalid = client.post("/entries/1/edit", data={"name": "새 이름", "message": "  "})
    assert invalid.status_code == 422
    assert 'action="/entries/1/edit"' in invalid.text
    assert 'value="새 이름"' in invalid.text
    result = client.post("/entries/1/edit", data={"name": "새 이름", "message": '<script>x</script> 바뀐 신호'})
    assert result.status_code == 200
    assert "인사를 수정했습니다" in result.text
    assert "&lt;script&gt;x&lt;/script&gt; 바뀐 신호" in result.text
    with sqlite3.connect(main.database_path()) as connection:
        assert connection.execute("SELECT count(*), created_at FROM entries").fetchone() == (1, stored[1])
    result = client.post("/entries/1/delete", follow_redirects=False)
    assert result.status_code == 303
    assert "deleted=true" in result.headers["location"]
    assert "첫 번째 마음을 기다리고 있어요" in client.get("/").text
    assert client.post("/entries/1/delete").status_code == 404


def test_other_browser_cannot_change_an_entry(client):
    client.post("/entries", data={"name": "작성자", "message": "내 이야기"})
    with TestClient(main.app) as other:
        assert "/entries/1/edit" not in other.get("/").text
        assert other.get("/entries/1/edit").status_code == 403
        assert other.post("/entries/1/edit", data={"name": "다른 사람", "message": "변조"}).status_code == 403
        assert other.post("/entries/1/delete").status_code == 403
        other.post("/entries", data={"name": "두 번째 작성자", "message": "다른 이야기"})
        assert other.post("/entries/1/delete").status_code == 403
        assert "/entries/2/edit" in other.get("/").text
        other.cookies.set(main.OWNER_COOKIE, "a" * 43)
        assert other.post("/entries/1/delete").status_code == 403
    assert "내 이야기" in client.get("/").text
    assert client.get("/entries/999/edit").status_code == 404
    assert client.get("/entries/1/delete").status_code == 405


def test_edit_and_delete_reject_cross_origin(client):
    client.post("/entries", data={"name": "작성자", "message": "변경 전"})
    assert client.post("/entries/1/edit", data={"name": "변조", "message": "나쁜 요청"}, headers={"origin": "https://other.example"}).status_code == 403
    assert client.post("/entries/1/delete", headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert "변경 전" in client.get("/").text


def test_legacy_database_is_preserved(client):
    with sqlite3.connect(main.database_path()) as connection:
        connection.execute("CREATE TABLE entries (id INTEGER PRIMARY KEY, name TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL)")
        connection.execute("INSERT INTO entries VALUES (1, '기존 손님', '보존되는 이야기', '2026-10-23T12:00:00+09:00')")
    response = client.get("/")
    assert "보존되는 이야기" in response.text
    assert "/entries/1/edit" not in response.text
    client.post("/entries", data={"name": "새 손님", "message": "새 이야기"})
    assert client.post("/entries/1/delete").status_code == 403
    with sqlite3.connect(main.database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM entries").fetchone()[0] == 2
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("entries",)]


def test_space_assets_are_served_and_traversal_is_blocked(client):
    for path, content_type in [("space.js", "javascript"), ("space-background.png", "image/png")]:
        response = client.get("/static/" + path)
        assert response.status_code == 200
        assert content_type in response.headers["content-type"]
    assert client.get("/static/%2e%2e/main.py").status_code == 404


def test_secure_cookie_on_https(client):
    with TestClient(main.app, base_url="https://testserver") as secure_client:
        response = secure_client.post("/entries", data={"name": "손님", "message": "안전한 신호"}, follow_redirects=False)
        assert "; Secure" in response.headers["set-cookie"]


def social_data(entry_id=1):
    with sqlite3.connect(main.database_path()) as connection:
        row = connection.execute("SELECT likes_json, replies_json FROM entries WHERE id=?", (entry_id,)).fetchone()
    return json.loads(row[0]), json.loads(row[1])


def test_like_check_uncheck_and_idempotence(client):
    client.post("/entries", data={"name": "손님", "message": "별 이야기"})
    headers = {"accept": "application/json"}
    for _ in range(2):
        response = client.post("/entries/1/like", data={"liked": "true"}, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"liked": True, "count": 1}
    assert 'aria-pressed="true"' in client.get("/").text
    digest = social_data()[0][0]
    assert len(digest) == 64 and digest not in client.get("/").text
    for _ in range(2):
        assert client.post("/entries/1/like", data={"liked": "false"}, headers=headers).json() == {"liked": False, "count": 0}


def test_like_from_new_browser_persists_and_counts_separately(client):
    client.post("/entries", data={"name": "작성자", "message": "인사"})
    client.post("/entries/1/like", data={"liked": "true"})
    with TestClient(main.app) as other:
        result = other.post("/entries/1/like", data={"liked": "true"}, headers={"accept": "application/json"})
        assert result.json() == {"liked": True, "count": 2}
        assert "HttpOnly" in result.headers["set-cookie"]
        assert 'aria-pressed="true"' in other.get("/").text
        assert other.post("/entries/1/like", data={"liked": "false"}, headers={"accept": "application/json"}).json()["count"] == 1
    assert 'aria-pressed="true"' in client.get("/").text


def test_like_limit_and_invalid_requests(client, monkeypatch):
    client.post("/entries", data={"name": "손님", "message": "인사"})
    monkeypatch.setattr(main, "MAX_LIKES", 1)
    client.post("/entries/1/like", data={"liked": "true"})
    with TestClient(main.app) as other:
        assert other.post("/entries/1/like", data={"liked": "true"}).status_code == 409
    assert client.post("/entries/1/like", data={"liked": "false"}).status_code == 200
    assert client.post("/entries/1/like", data={"liked": "oops"}).status_code == 422
    assert client.post("/entries/1/like", json={"liked": True}).status_code == 415
    assert client.post("/entries/999/like", data={"liked": "true"}).status_code == 404
    assert client.post("/entries/1/like", data={"liked": "true"}, headers={"origin": "https://other.example"}).status_code == 403
    assert social_data()[0] == []


def test_reply_create_edit_delete_and_context(client):
    client.post("/entries", data={"name": "원글", "message": "별 이야기"})
    response = client.post("/entries/1/replies?page=1&q=%EB%B3%84", data={"name": "  답장자  ", "message": "작은\n답장"}, follow_redirects=False)
    assert response.status_code == 303
    assert "page=1" in response.headers["location"] and "q=%EB%B3%84" in response.headers["location"]
    assert "thread=1#note-1" in response.headers["location"]
    reply = social_data()[1][0]
    assert reply["name"] == "답장자" and reply["message"] == "작은\n답장"
    reply_id = reply["id"]
    page = client.get(response.headers["location"]).text
    assert '<details class="reply-thread" id="thread-1" open>' in page
    assert "작은\n답장" in page
    assert reply["owner_hash"] not in page
    result = client.post(f"/entries/1/replies/{reply_id}/edit", data={"name": "새 답장자", "message": "수정한 답장"})
    assert result.status_code == 200
    updated = social_data()[1][0]
    assert updated["message"] == "수정한 답장"
    assert updated["created_at"] == reply["created_at"]
    assert updated["id"] == reply_id
    assert client.post(f"/entries/1/replies/{reply_id}/delete").status_code == 200
    assert social_data()[1] == []


def test_reply_permissions_and_parent_delete(client):
    client.post("/entries", data={"name": "원글 작성자", "message": "인사"})
    with TestClient(main.app) as other:
        response = other.post("/entries/1/replies", data={"name": "답장자", "message": "다른 사람의 답글"})
        assert response.status_code == 200 and other.cookies.get(main.OWNER_COOKIE)
        reply_id = social_data()[1][0]["id"]
        assert client.post(f"/entries/1/replies/{reply_id}/edit", data={"name": "변조", "message": "  "}).status_code == 403
        assert client.post(f"/entries/1/replies/{reply_id}/delete").status_code == 403
        assert other.post(f"/entries/1/replies/{reply_id}/delete", headers={"sec-fetch-site": "cross-site"}).status_code == 403
        assert other.post(f"/entries/1/replies/{reply_id}/edit", data={"name": "답장자", "message": "변조"}, headers={"origin": "https://other.example"}).status_code == 403
        client.post("/entries/1/like", data={"liked": "true"})
        client.post("/entries/1/delete")
        assert other.post(f"/entries/1/replies/{reply_id}/delete").status_code == 404
    with sqlite3.connect(main.database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM entries").fetchone()[0] == 0


def test_reply_validation_escaping_and_limit(client, monkeypatch):
    client.post("/entries", data={"name": "원글", "message": "인사"})
    for payload in [{"name": "", "message": "보존되는 답글"}, {"name": "손님", "message": " "}, {"name": "가" * 25, "message": "답장"}, {"name": "손님", "message": "가" * 501}]:
        response = client.post("/entries/1/replies", data=payload)
        assert response.status_code == 422
        assert '<details class="reply-thread" id="thread-1" open>' in response.text
    assert social_data()[1] == []
    response = client.post("/entries/1/replies", data={"name": "", "message": "보존되는 답글"})
    assert ">보존되는 답글</textarea>" in response.text
    monkeypatch.setattr(main, "MAX_REPLIES", 2)
    client.post("/entries/1/replies", data={"name": '<img src=x>', "message": '<script>x</script> ${name} {{entries}}'})
    page = client.get("/?thread=1").text
    assert "<script>x</script>" not in page and "&lt;script&gt;x&lt;/script&gt;" in page
    assert "&lt;img src=x&gt;" in page
    client.post("/entries/1/replies", data={"name": "가" * 24, "message": "😀" * 500})
    assert client.post("/entries/1/replies", data={"name": "손님", "message": "한도 초과"}).status_code == 409
    assert len(social_data()[1]) == 2
    assert client.post("/entries/999/replies", data={"name": "", "message": ""}).status_code == 404


def test_concurrent_social_updates_do_not_lose_changes(client):
    client.post("/entries", data={"name": "원글", "message": "인사"})
    def react(number):
        token = str(number).zfill(43)
        main.social_mutation(1, token, "like", desired_like=True)
        main.social_mutation(1, token, "reply", entry=main.EntryIn(name=f"답장자{number}", message=f"답글{number}"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(react, range(8)))
    likes, replies = social_data()
    assert len(likes) == 8 and len(set(likes)) == 8
    assert {reply["message"] for reply in replies} == {f"답글{number}" for number in range(8)}
    with sqlite3.connect(main.database_path()) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("entries",)]
