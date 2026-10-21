# Field 범위, 길이 패턴에 대해서 엄격하게 검사
from pydantic import BaseModel, Field, ValidationError, EmailStr, ConfigDict
from typing import Literal

class Registration(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid') # extra='forbid' : 필드에 없는 값이 들어오면 에러 발생
    name : str = Field(min_length=2, max_length=20, description='실명')
    age : int = Field(ge=14, le=100)
    email : EmailStr
    level : Literal['basic', 'premium'] = 'basic'
    code : str = Field(pattern=r'^STU[0-9]{4}$')
    agreed : bool = Field(strict=True)

def main() -> None:
   user_01 = Registration(name='LEE', age=20, email='lee@abc.com', code='STU0007', agreed=True)
   print('검증성공', user_01.model_dump())
   print('오류확인')

   try:
      user_02 = Registration(name='LEE', age=20, email = 'lee@abc.com', code ='STU0007', agreed=True)
   except ValidationError as e:
      print(e.errors()[0]['loc'], e.errors()[0]['type'])

if __name__ == '__main__':
   main()      
                    