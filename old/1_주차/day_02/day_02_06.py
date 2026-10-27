# 딕셔너리 <key - value 한쌍이 하나의 값>

# 리스트 / 딕셔너리
# list_1 = [10, 20, 30, [1, 2, 3]] 
# dict_1 = {"kor":80, "eng":80, "mach":90}

# dict_1.keys() <= key 만 불러오는
# dict_1.values() <= value 만 불러오는
# dict_1.items() <= key - value 함께 불러오는


list_1 = [10, 20, 30, [1, 2, 3]] 
dict_1 = {"kor":80, "eng":80, "math":90}

# for i in dict_1:
#     print(i)   #kor eng mach

# for i in dict_1.values():
#     print(i)    #80 80 90

# for i in dict_1.items():
#     print(i)    # ('kor', 80) ('eng', 80) ('math', 90)

for key, value in dict_1.items():
    print(f"key = {key}, value = {value}")  
