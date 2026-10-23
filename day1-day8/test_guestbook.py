"""수업의 pytest/TestClient 패턴. 실제 DB와 분리된 임시 SQLite를 사용합니다."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
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
    assert client.get("/").text.count('<article class="note">') == 1


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
    assert first.count('<article class="note">') == 6
    assert first.index("인사7") < first.index("인사2")
    second = client.get("/?page=2").text
    assert second.count('<article class="note">') == 2
    assert "인사0" in second
    assert 'rel="prev"' in second
    result = client.get("/", params={"q": "손님3"}).text
    assert result.count('<article class="note">') == 1
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
