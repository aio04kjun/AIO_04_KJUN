# 요청 3개를 동시에 보내는 경우

import asyncio
from time import perf_counter
import httpx

def request_one(client, path, number):
    start = perf_counter()
    response = await client.get(path)
    response.raise_for_status()
    elapsed = perf_counter() - start
    print(f'{path}요청 {number}: {response.status_code}, {elapsed:.2f}')
    return response.json()


