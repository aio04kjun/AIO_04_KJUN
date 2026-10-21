"""06장 학생 실습: 부분수정과 직렬화 차이 확인."""
from pydantic import BaseModel


class Profile(BaseModel):
    nickname: str
    bio: str | None = None
    active: bool = True


class ProfilePatch(BaseModel):
    nickname: str | None = None
    bio: str | None = None
    active: bool | None = None


def main() -> None:
    stored = Profile(nickname='old', bio='소개 글', active=True)
    patch = ProfilePatch(nickname='new')
    print(patch.model_dump(exclude_unset=True))
    updated = Profile.model_validate({**stored.model_dump(), **patch.model_dump(exclude_unset=True)})
    print('ProfilePatch(bio=None):', ProfilePatch(bio=None).model_dump(exclude_unset=True))
    print('ProfilePatch():', ProfilePatch().model_dump(exclude_unset=True))
    print('기존:', stored.model_dump(), '패치:', patch)


if __name__ == '__main__':
    main()
