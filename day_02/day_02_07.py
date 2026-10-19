# 백엔드 API에서 요청을 보낸 사용자 정보(dict)를 검증해서 접근 가능 여부
# 부여할 기능을 판별하는 분기 로직을 생성

# 요구사항
# 1. 사용자 정보는 user_role(문자열)과 is_suspended(정지계정여부)
# 2. is_suspended가 True면 즉시 "정지된 계정 입니다."를 출력하고 검사를 종료
# 3. 역할은 admin, manager, user, guest 중 하나
#   admin: "전체 시스템 관리 및 데이터 수정 권한 부여"
#   manager: "팀 데이터 조회 및 수정 권한 부여"
#   user: "개인 데이터 조회 권한 부여"
#   guest: "게스트 권한 (읽기 전용 일부 허용)"
# 4. 정의되지 않은 역할일 경우 : [오류] 알 수없는 권한 입니다. 

test_users = [
    {"username": "alpha", "user_role": "admin", "is_suspended": False},
    {"username": "bravo", "user_role": "user", "is_suspended": True},
    {"username": "charlie", "user_role": "manager", "is_suspended": False},
    {"username": "delta", "user_role": "hacker", "is_suspended": False},
]

# for user in test_users:
#     username = user["username"]
#     role = user["user_role"]
#     suspended = user["is_suspended"]


# 역할별 권한 메시지
role_messages = {
    "admin": "전체 시스템 관리 및 데이터 수정 권한 부여",
    "manager": "팀 데이터 조회 및 수정 권한 부여",
    "user": "개인 데이터 조회 권한 부여",
    "guest": "게스트 권한 (읽기 전용 일부 허용)",
}

# for user in test_users:
#     print(f"[{user['username']}]")

#     # 정지된 계정은 권한을 확인하지 않음
#     if user["is_suspended"]:
#         print("정지된 계정 입니다.")
#         continue

#     # 정의되지 않은 역할이면 오류 메시지 출력
#     message = role_messages.get(
#         user["user_role"],
#         "[오류] 알 수없는 권한 입니다."
#     )
#     print(message)



for user in test_users:
    if user["is_suspended"]:
        print(f"{user['username']}: 정지된 계정 입니다.")
        continue

    message = role_messages.get(
        user["user_role"],
        "[오류] 알 수없는 권한 입니다."
    )
    print(f"{user['username']}, {user['user_role']} : {message}")



