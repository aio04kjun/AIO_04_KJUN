# 숫자 맞추기 게임
# 규칙
# 컴퓨터가 1~100까지 임의 값 생성
# 사용자가 맞추는 게임
# 입력값에 따라 업, 다운

# 필요한 기능
# 입력 : int(input())
# 컴퓨터 임의 숫자 선택(1~100)
# 비교연산자를 통해 업,다운 판별
# 순환문, 조건문, break

import random
com_number = random.randint(1, 100)
count = 0

while True:
    user_number = int(input("1~100 : "))
    # count = count + 1
    count += 1

    if user_number > com_number:
        print("컴퓨터 숫자 보다 큽니다.")

    elif user_number < com_number:
        print("컴퓨터 숫자 보다 작습니다.")    
        
    else:
        print(f"정답입니다. 총 시도 횟수는 : {count}")    
        break


