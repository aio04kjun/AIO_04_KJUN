# menu = ["아메리카노", "라떼", "초코"]
# ice_menu = ["아이스" + i for i in menu]
# print(ice_menu)

# ages = [20, 15, 60, 25, 30, 35, 5]
# print([i for i in ages if i>=20])
# print(["성인" if i>=20 else "미성년" for i in ages])

# print(set([1,2,3,4,5,6,7,8,9,1,2,3,4,6]))


bad_words = ["바보","멍충이", "멍텅구리", "멍충이", ""]
words = sorted(set(word for word in bad_words if word), key=len, reverse=True)
# print(words)

import re
# print(re.escape(word) for word in words)

# print(" | ".join(words))
pattern = "|".join(re.escape(word) for word in words)
# print(pattern)

chat_message = "철수는 바보 입니다."
result = re.sub(pattern, lambda match: "*" * len(match.group(0)),
                chat_message, flags=re.IGNORECASE)
print(result)
