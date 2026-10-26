from fastapi import FastAPI

app = FastAPI()
tasks = {1: {"id": 1, "title": "Git 준비"}}

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    return tasks.get(task_id)
