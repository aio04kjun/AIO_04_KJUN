"""05장 학생 실습: 강좌와 수강생의 중첩 관계 모델링."""
from pydantic import BaseModel, Field


class Learner(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)


class Course(BaseModel):
    title: str
    learners: list[Learner] = Field(min_length=1)


def main() -> None:
    raw = {'title': '파이썬 기초', 'learners': [{'name': '홍길동', 'score': 90},{'name': '김철수', 'score': 85},],}
    course = Course.model_validate(raw)
    print('강좌:', course.title)
    for learner in course.learners:
        print('수강생:', learner.name, '점수:', learner.score)


if __name__ == '__main__':
    main()
