"""06장: model_dump/json/validate, ConfigDict 및 안전한 PATCH."""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class Task(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1)
    done: bool = False
    due: date | None = None


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str | None = Field(default=None, min_length=1)
    done: bool | None = None
    due: date | None = None

    @model_validator(mode='after')
    def reject_nulls(self) -> 'TaskPatch':
        # 강의 예시에서는 null을 허용하지 않으며, 생략한 필드만 그대로 유지한다.
        changes = self.model_dump(exclude_unset=True)
        if 'title' in changes and self.title is None:
            raise ValueError('title을 null로 변경할 수 없습니다')
        if 'done' in changes and self.done is None:
            raise ValueError('done을 null로 변경할 수 없습니다')
        return self


def main() -> None:
    task = Task(title='  자료 준비  ', due='2026-11-01')
    print('STEP 1 - 딕셔너리:', task.model_dump())
    print('STEP 2 - JSON:', task.model_dump_json())
    print('STEP 3 - model_validate:', Task.model_validate({'title': '발표', 'done': True}))
    patch = TaskPatch(done=True)
    print('STEP 4 - 부분수정 payload:', patch.model_dump(exclude_unset=True))
    print('exclude_none 와의 차이:', TaskPatch(due=None).model_dump(exclude_unset=True))
    merged = {**task.model_dump(), **patch.model_dump(exclude_unset=True)}
    updated = Task.model_validate(merged)
    print('STEP 5 - 재검증 후 수정:', updated.model_dump())
    try:
        Task(title='자료 준비', unexpected=10)
    except ValidationError as error:
        print('STEP 6 - extra forbid:', error.errors()[0]['type'])
    print('06장 성공')


if __name__ == '__main__':
    main()