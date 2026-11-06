import time


# 1. yield 없음: 숫자를 모두 만든 뒤 리스트를 반환한다.
def without_yield():
    numbers = []

    for number in range(1, 4):
        time.sleep(1)  # 숫자 하나를 만드는 데 1초가 걸린다고 가정
        print(f"  만드는 중: {number}")
        numbers.append(number)

    return numbers


# 2. yield 있음: 숫자를 하나 만들 때마다 전달한다.
def with_yield():
    for number in range(1, 4):
        time.sleep(1)
        print(f"  만드는 중: {number}")
        yield number


print("=== yield 없음 ===")

for value in without_yield():  # [1,2,3]
    print(f"받아서 출력: {value}")


print("\n=== yield 있음 ===")

for value in with_yield():
    print(f"받아서 출력: {value}")