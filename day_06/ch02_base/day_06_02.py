# 필수 / 기본값, 모델 생성/ 검증
from pydantic import BaseModel, ValidationError

class Member(BaseModel):
    username: str
    age: int
    active: bool = True # 기본값 설정
    nickname: str | None = None # 선택적 필드, 기본값 None


class MemberOut(Member):
    id : int    

def main() -> None:
    member = Member(username = "KIM", age = 23)
    print(member)
    raw = {"username": "LEE", "age": 25, "active": False}
    parsed = Member.model_validate(raw)
    print(parsed, 'age 타입', type(parsed.age).__name__)
    print("nickname 기본값", parsed.nickname)

    # 필수 필드 누락
    # try:
    #     Member(username = "PARK")
    # except ValidationError as e:
    #     print(e.errors()[0]['loc'], e.errors()[0]['type'])

    memberout = MemberOut(id = 2, username = "KIM", age = 23)
    print(memberout)


if __name__ == "__main__":
    main()
