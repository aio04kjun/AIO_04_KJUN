"""main.py의 동기식 버전.

실행: uvicorn main_sync:app --reload (이 파일이 있는 폴더에서 실행)
확인: http://127.0.0.1:8000/todos/1

비교 실험 (외부 서버 연결 없이 실행):
    http://127.0.0.1:8000/demo/sync  → 약 3초
    http://127.0.0.1:8000/demo/async → 약 1초
각 작업의 1초 대기는 외부 서버의 답을 기다리는 상황을 흉내 냅니다.
이 차이는 '순서대로 실행'과 '기다림을 겹쳐 실행'을 비교한 것입니다.
main.py에서 async를 쓴 것만으로 작업 여러 개가 자동으로 시작되지는 않습니다.
"""

import asyncio
import time

import httpx
from fastapi import FastAPI, HTTPException

BASE_URL = "https://jsonplaceholder.typicode.com"

app = FastAPI()


def record_event(events: list[str], started: float, message: str):
    """터미널과 응답에 작업 순서, 경과 시간을 표시합니다."""
    event = f"{time.perf_counter() - started:.2f}초: {message}"
    events.append(event)
    print(event, flush=True)


@app.get("/demo/sync")
def demo_sync():
    """동기식: 하나를 끝낸 뒤 다음 작업을 시작합니다."""
    started = time.perf_counter()
    events = []
    for number in range(1, 4):
        record_event(events, started, f"[동기식] {number}번 주문 시작")
        time.sleep(1)  # 이 작업을 맡은 스레드는 1초 동안 기다립니다.
        record_event(events, started, f"[동기식] {number}번 주문 완료")

    return {
        "방식": "동기식: 1번 완료 → 2번 시작 → 2번 완료 → 3번 시작",
        "걸린_시간_초": round(time.perf_counter() - started, 2),
        "실행_기록": events,
    }


async def wait_for_order(number: int, events: list[str], started: float):
    record_event(events, started, f"[비동기식] {number}번 주문 시작")
    await asyncio.sleep(1)  # 기다리는 동안 다른 주문을 진행할 수 있습니다.
    record_event(events, started, f"[비동기식] {number}번 주문 완료")


@app.get("/demo/async")
async def demo_async():
    """비교용 비동기식: 세 작업의 기다리는 시간을 겹칩니다."""
    started = time.perf_counter()
    events = []
    # await만 쓰면 자동으로 동시 실행되지 않습니다.
    # gather로 세 작업을 함께 진행하도록 예약합니다.
    await asyncio.gather(
        *(wait_for_order(number, events, started) for number in range(1, 4))
    )

    return {
        "방식": "비동기식: 1·2·3번을 시작하고 기다리는 시간을 겹침",
        "걸린_시간_초": round(time.perf_counter() - started, 2),
        "실행_기록": events,
    }


# async def 대신 def: 요청한 결과가 올 때까지 이 함수는 기다립니다.
def fetch_todo(todo_id: int):
    # AsyncClient → Client, async with → with
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # await 없이 호출합니다. 응답을 받은 뒤에 다음 줄로 넘어갑니다.
        response = client.get(f"/todos/{todo_id}")
        print(response.status_code)
        response.raise_for_status()
        return response.json()


@app.get("/todos/{todo_id}")
def read_todo(todo_id: int):
    try:
        data = fetch_todo(todo_id)
    except httpx.HTTPError as exc:
        # 연결 실패 때는 응답 자체가 없을 수 있으므로 exc.response를 읽지 않습니다.
        raise HTTPException(
            status_code=502,
            detail="외부 서버에서 할 일을 가져오지 못했습니다.",
        ) from exc

    return {
        "id": data.get("id", todo_id),
        "title": data.get("title", "제목없음"),
        "completed": data.get("completed", False),
    }
