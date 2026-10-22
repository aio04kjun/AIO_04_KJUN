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
    await make_drink('아메리카노')
    await make_drink('카페라떼')

if __name__ == '__main__':
    asyncio.run(main())  #비동기식 호출

