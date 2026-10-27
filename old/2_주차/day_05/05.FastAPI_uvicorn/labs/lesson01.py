from fastapi import FastAPI

app = FastAPI(title="Lesson 01")

@app.get("/")
def root():
    return {"message": "Hello FastAPI"}

@app.get("/sports")
def sports():
    return {"sports": ["Soccer", "Basketball", "Tennis", "Baseball", "Swimming"]}

@app.get("/menu")
def menu():
    return {"menu": ["Pizza", "Burger", "Salad", "Pasta", "Sushi"]}