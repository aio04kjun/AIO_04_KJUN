# RIOC
# R(role) : 역활
# I(input) : 입력
# O(output) : 출력
# C(constraints) : 제약조건

# 리스트 컴프리핸션
# result = []

list_1 = [1, 2, 3, 4, 5]
# for i in list_1:
#     if i % 2 == 0:
#         result.append(i)

# result = [i for i in list_1 if i%2 == 0]
result = [i*2 for i in list_1]
print(result)        