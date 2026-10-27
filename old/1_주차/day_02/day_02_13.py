# import random
# ages = random.sample(range(15,100), 10)
# result = []
# for i in ages:
#     if i >= 20:
#         result.append("성인")
#     else:
#         result.append("미성년자")
# print(result)

# items = ["정상", "불량", "불량", "정상"]

# for item in items:
#     if item == "불량":
#         items.remove("불량")

# print(f"검수결과 : {items}")   
# 
# 
# items = ["정상", "불량", "불량", "정상"]
# target = items[:]
# for item in target:
#     if item == "불량":
#         items.remove("불량")

# print(f"검수결과 : {items}")          


items = ["정상", "불량", "불량", "정상"]
result = []
for item in items:
    if item !="불량":
        result.append(item)

print(f"검수결과 : {result}")        