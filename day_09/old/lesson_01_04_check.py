"""lesson_01_04.py의 CRUD API 테스트.

프로젝트 루트에서 실행: python day_09/lesson_01_04_check.py
별도로 uvicorn 서버를 실행할 필요는 없습니다.
"""

import unittest

from fastapi.testclient import TestClient

try:
    from . import lesson_01_04 as target
except ImportError:
    import lesson_01_04 as target


class TaskCRUDTest(unittest.TestCase):
    def setUp(self):
        # 각 테스트가 다른 테스트의 데이터에 영향을 받지 않도록 초기화합니다.
        target.tasks.clear()
        self.client = TestClient(target.app, raise_server_exceptions=False)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.addCleanup(target.tasks.clear)
        self.task = {"id": 3, "name": "홍길동", "message": "공부하기"}

    def seed_task(self):
        # 조회/수정/삭제는 생성 기능에 오류가 있어도 독립적으로 검사합니다.
        target.tasks.append(self.task.copy())

    # C: 생성 (POST)
    def test_create_task(self):
        response = self.client.post("/tasks", json=self.task)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), self.task)
        self.assertEqual(self.client.get("/tasks").json(), [self.task])

    def test_create_second_task(self):
        self.seed_task()
        new_task = {"id": 10, "name": "김철수", "message": "운동하기"}
        response = self.client.post("/tasks", json=new_task)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), new_task)
        self.assertEqual(self.client.get("/tasks").json(), [self.task, new_task])

    def test_create_duplicate_id_returns_409(self):
        self.seed_task()
        response = self.client.post("/tasks", json=self.task)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Task ID already exists"})
        self.assertEqual(self.client.get("/tasks").json(), [self.task])

    def test_create_invalid_input_returns_422(self):
        for changes in ({"id": 0}, {"name": ""}, {"message": ""}):
            with self.subTest(changes=changes):
                response = self.client.post("/tasks", json={**self.task, **changes})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(target.tasks, [])
        response = self.client.post("/tasks", json={"id": 1})
        self.assertEqual(response.status_code, 422)

    # R: 조회 (GET)
    def test_read_empty_list(self):
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_read_all_tasks(self):
        self.seed_task()
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [self.task])

    def test_read_task_by_id(self):
        self.seed_task()
        response = self.client.get("/tasks/3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.task)

    # U: 전체 수정 (PUT), 부분 수정 (PATCH)
    def test_replace_task(self):
        self.seed_task()
        updated = {"id": 3, "name": "김철수", "message": "복습하기"}
        response = self.client.put("/tasks/3", json=updated)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), updated)
        self.assertEqual(self.client.get("/tasks/3").json(), updated)

    def test_replace_mismatched_id_returns_400(self):
        self.seed_task()
        response = self.client.put("/tasks/3", json={**self.task, "id": 10})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Task ID mismatch"})
        self.assertEqual(self.client.get("/tasks/3").json(), self.task)

    def test_replace_missing_field_returns_422(self):
        self.seed_task()
        response = self.client.put("/tasks/3", json={"id": 3, "name": "김철수"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/tasks/3").json(), self.task)

    def test_patch_preserves_other_fields(self):
        self.seed_task()
        for field, value in (("name", "김철수"), ("message", "복습하기")):
            with self.subTest(field=field):
                response = self.client.patch("/tasks/3", json={field: value})
                self.task[field] = value
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), self.task)
                self.assertEqual(self.client.get("/tasks/3").json(), self.task)

    def test_patch_empty_string_returns_422(self):
        self.seed_task()
        for field in ("name", "message"):
            with self.subTest(field=field):
                response = self.client.patch("/tasks/3", json={field: ""})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(self.client.get("/tasks/3").json(), self.task)

    # D: 삭제 (DELETE). 리스트 위치가 아닌 ID로 삭제하는지도 검사합니다.
    def test_delete_task_by_id(self):
        self.seed_task()
        remaining = {"id": 10, "name": "김철수", "message": "운동하기"}
        target.tasks.append(remaining.copy())
        response = self.client.delete("/tasks/3")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get("/tasks").json(), [remaining])
        self.assertEqual(self.client.get("/tasks/3").status_code, 404)
        self.assertEqual(self.client.delete("/tasks/3").status_code, 404)

    def test_missing_task_returns_404(self):
        self.seed_task()
        requests = (
            ("GET", None),
            ("PUT", {**self.task, "id": 999}),
            ("PATCH", {"name": "수정"}),
            ("DELETE", None),
        )
        for method, payload in requests:
            with self.subTest(method=method):
                response = self.client.request(method, "/tasks/999", json=payload)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": "Task not found"})
                self.assertEqual(self.client.get("/tasks").json(), [self.task])


if __name__ == "__main__":
    unittest.main(verbosity=2)
