import asyncio
import time
from time import perf_counter

# 동기
# def make_drink(name):
#     print(f'{name} 만들기 시작')
#     time.sleep(2)
#     print(f'{name} 완료')
#     return name

# def main():
#     make_drink('아메리카노')
#     make_drink('카페라떼')

# if __name__ == '__main__':
#     main()


# 비동기
async def make_drink(name):
    print(f'{name} 만들기 시작')
    await asyncio.sleep(2)  
    print(f'{name} 완료')
    return name

async def main():
    # start = perf_counter()
    # await make_drink('아메리카노')
    # await make_drink('카페라떼')
    # print(f'순서대로 기다림: {perf_counter() - start:.2f}초\n')

    start = perf_counter()
    result = await asyncio.gather(make_drink('아메리카노'), make_drink('카페라떼'))
    print(f'동시에 기다림: {perf_counter() - start:.2f}초\n')
    print('결과', result)

if __name__ == '__main__':
    asyncio.run(main())  #비동기식 호출

