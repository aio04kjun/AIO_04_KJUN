from fastapi import FastAPI

app = FastAPI(title="Lesson 02")

@app.get("/method")
def read_method():
    return {"method": "GET", "purpose": "read"}


# swagger ui에서 post method를 테스트할 때, status_code=201을 지정하지 않으면 200으로 반환됨

@app.post("/method", status_code=201)
def create_method():
    return {"method": "POST", "purpose": "create"}