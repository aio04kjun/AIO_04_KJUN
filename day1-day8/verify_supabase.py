"""실제 Supabase 연결 및 HTTP 기능 검증. 테스트 글 변경은 모두 롤백합니다."""
import json

from fastapi.testclient import TestClient

import main


def verify():
    original = main.connect_db
    connection = original()

    class RollbackOnly:
        def execute(self, *args, **kwargs):
            return connection.execute(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def close(self):
            pass

    try:
        assert connection.execute("SELECT to_regclass('public.entries') AS name").fetchone()["name"] == "entries"
        main.connect_db = RollbackOnly
        with TestClient(main.app) as client:
            assert client.get("/").status_code == 200
            token = main.secrets.token_urlsafe(32)
            client.cookies.set(main.OWNER_COOKIE, token)
            response = client.post("/entries", data={"name": "연결검증", "message": "Supabase %_ 검증"})
            assert response.status_code == 200
            row = connection.execute("SELECT id FROM public.entries WHERE owner_hash=%s", (main.owner_hash(token),)).fetchone()
            assert row is not None
            entry_id = row["id"]
            assert "Supabase %_ 검증" in client.get("/", params={"q": "%_"}).text
            assert client.post(f"/entries/{entry_id}/edit", data={"name": "연결검증", "message": "수정 완료"}).status_code == 200
            result = client.post(f"/entries/{entry_id}/like", data={"liked": "true"}, headers={"accept": "application/json"})
            assert result.json() == {"liked": True, "count": 1}
            assert client.post(f"/entries/{entry_id}/replies", data={"name": "답글검증", "message": "답글 완료"}).status_code == 200
            replies = json.loads(connection.execute("SELECT replies_json FROM public.entries WHERE id=%s", (entry_id,)).fetchone()["replies_json"])
            reply_id = replies[0]["id"]
            assert client.post(f"/entries/{entry_id}/replies/{reply_id}/edit", data={"name": "답글검증", "message": "답글 수정"}).status_code == 200
            assert client.post(f"/entries/{entry_id}/replies/{reply_id}/delete").status_code == 200
            assert client.post(f"/entries/{entry_id}/delete").status_code == 200
        print("PASS: public.entries, page, create, search, edit, like, replies, delete")
    finally:
        main.connect_db = original
        connection.rollback()
        connection.close()
        print("Test changes rolled back")


if __name__ == "__main__":
    verify()
