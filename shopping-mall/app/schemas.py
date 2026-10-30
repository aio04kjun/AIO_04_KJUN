import re
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=100)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=2147483647)]
Money = Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Credentials(Input):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('올바른 이메일을 입력해 주세요.')
        return value


class Signup(Credentials):
    name: Name
    password: str = Field(min_length=8, max_length=128)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError('이름은 비워 둘 수 없습니다.')
        return value.strip()


class Login(Credentials):
    next: str = Field(default='/', max_length=2048)


class ProfileUpdate(Input):
    name: Name | None = None
    phone: str | None = Field(default=None, max_length=30)

    @model_validator(mode='after')
    def valid_update(self):
        if not self.model_fields_set:
            raise ValueError('수정할 항목을 입력해 주세요.')
        if 'name' in self.model_fields_set:
            if self.name is None or not self.name.strip():
                raise ValueError('이름은 비워 둘 수 없습니다.')
            self.name = self.name.strip()
        if self.phone is not None:
            self.phone = self.phone.strip() or None
        return self


class Withdraw(Input):
    password: str = Field(min_length=1, max_length=128)


class CartAdd(Input):
    product_id: UUID
    quantity: Quantity


class CartUpdate(Input):
    quantity: Quantity


class OrderItem(Input):
    product_id: UUID
    quantity: Quantity


class OrderCreate(Input):
    order_id: UUID
    items: list[OrderItem] = Field(min_length=1, max_length=100)
    recipient_name: Name
    recipient_phone: str = Field(min_length=1, max_length=30)
    shipping_address: str = Field(min_length=1, max_length=1000)
    expected_total: Money

    @field_validator('recipient_name', 'recipient_phone', 'shipping_address')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('공백만 입력할 수 없습니다.')
        return value.strip()

