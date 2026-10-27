# class PromptEmptyError(Exception):
#     pass

# prompt = " "
# try:
#     print(1/0)

#     if not prompt.strip():
#         raise PromptEmptyError()

# except PromptEmptyError as e:
#     print("반드시 입력을 하셔야 합니다.")

# except ZeroDivisionError as e:
#     print("0으로 나눌수 없습니다.")    

# print("정상종료")

class AgeOverError(Exception):
     pass
for 
    try:
        age = int(input('나이를 입력하세요.'))
        if age > 100 or age < 0:
            raise AgeOverError()
    except AgeOverError as e:
        print("0과 100사이의 값을 입력 하세요.")
    except Exception as e:
        print("숫자만 입력하세요.")
    else:
        print("데이터가 정상 입니다.")
        break
    finally:
        print('총 시도횟수 :', i+1)    
