# FASTAPI
# Create  POST   status 201
# Rread   GET    
# Update  PUT/PATCH  
# Delete  DELETE

# 초기데이터 list[dic]
# dict --> id:int(1이상)  name : str (1글자이상), message :str (1글자이상)
# tasks = [
#     {'id':1, 'name':'홍길동', 'message':'동해번쩍'}
# ]
tasks = []

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="FastAPI CRUD Practice")

# 초기 데이터: list[dict]
tasks = []


# -----------------------------
# Pydantic 모델
# -----------------------------

# POST, PUT 요청 모델
class TaskInput(BaseModel):
    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    message: str = Field(min_length=1)


# PATCH 요청 모델
class TaskPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    message: str | None = Field(default=None, min_length=1)


# -----------------------------
# 공통 함수: ID로 데이터 검색
# -----------------------------
def find_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task

    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )


# -----------------------------
# CREATE: POST
# -----------------------------
@app.post("/tasks", status_code=201)
def create_task(payload: TaskInput):

    # ID 중복 검사
  
    # for task in tasks:
    #     if task["id"] == payload.id:
    #         raise HTTPException(
    #             status_code=409,
    #             detail="Task ID already exists"
    #         )

    if payload.id in[task["id"] for tast in tasks]:
        raise HTTPException(status_code=409, detail="Task ID already exists")

    task = payload.model_dump()
    tasks.append(task)

    return task


# -----------------------------
# READ: GET 전체 조회
# -----------------------------
@app.get("/tasks")
def get_tasks():
    return tasks


# -----------------------------
# READ: GET 개별 조회
# -----------------------------
@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    return find_task(task_id)


# -----------------------------
# UPDATE: PUT 전체 수정
# -----------------------------
@app.put("/tasks/{task_id}")
def replace_task(task_id: int, payload: TaskInput):

    task = find_task(task_id)

    # 경로 ID와 요청 데이터 ID 일치 확인
    if task_id != payload.id:
        raise HTTPException(
            status_code=400,
            detail="Task ID mismatch"
        )

    # 전체 데이터 교체
    task.clear()
    task.update(payload.model_dump())

    return task


# -----------------------------
# UPDATE: PATCH 부분 수정
# -----------------------------
@app.patch("/tasks/{task_id}")
def patch_task(task_id: int, payload: TaskPatch):

    task = find_task(task_id)

    # 요청에서 전달한 필드만 수정
    update_data = payload.model_dump(exclude_unset=True)

    task.update(update_data)

    return task


# -----------------------------
# DELETE: DELETE
# -----------------------------
@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):

    task = find_task(task_id)

    tasks.remove(task)