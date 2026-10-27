"""함수형 수정본을 회원 유형, 쿠폰, 주문 객체로 나눈 예제.

가격은 원 단위 정수, 수량은 양의 정수입니다.
회원 할인 → 원 미만 버림 → 쿠폰 차감 → 0원 하한 순서를 유지합니다.
"""

from dataclasses import dataclass
from enum import Enum


class MemberType(Enum):
    """[변경] 회원 유형과 지불 비율을 하나의 열거형으로 묶습니다."""

    # 각 값은 (기존 회원 코드, 할인 후 지불할 백분율)입니다.
    NON_MEMBER = (0, 100)
    TYPE_1 = (1, 95)
    TYPE_2 = (2, 90)
    TYPE_3 = (3, 80)

    @property
    def payment_percent(self) -> int:
        """외부에서는 비율을 조회하고, 계산은 주문 객체가 담당합니다."""
        return self.value[1]

    @classmethod
    def from_code(cls, u_type: int) -> "MemberType":
        """[변경] 기존 함수의 회원 코드 검증과 변환을 담당합니다."""
        if type(u_type) is not int:
            raise TypeError("u_type은 bool을 제외한 정수여야 합니다.")
        for member_type in cls:
            if member_type.value[0] == u_type:
                return member_type
        raise ValueError("u_type은 0, 1, 2, 3 중 하나여야 합니다.")


# [변경] frozen=True로 생성 후 값의 재대입을 막아 검증된 상태를 유지합니다.
@dataclass(frozen=True)
class Coupon:
    """쿠폰의 사용 여부와 정액 할인 정책을 표현합니다."""

    enabled: bool

    def __post_init__(self) -> None:
        # from_input()을 거치지 않고 직접 생성해도 잘못된 상태를 거부합니다.
        if type(self.enabled) is not bool:
            raise TypeError("enabled는 bool이어야 합니다.")

    @classmethod
    def from_input(cls, coupon: str | bool) -> "Coupon":
        """[변경] 함수 내부에 있던 쿠폰 입력 처리를 생성 메서드로 옮깁니다."""
        if isinstance(coupon, bool):
            return cls(enabled=coupon)
        if isinstance(coupon, str):
            normalized = coupon.strip().upper()
            if normalized not in ("YES", "NO"):
                raise ValueError("coupon 문자열은 YES 또는 NO여야 합니다.")
            return cls(enabled=normalized == "YES")
        raise TypeError("coupon은 YES/NO 문자열 또는 bool이어야 합니다.")

    @property
    def discount_amount(self) -> int:
        # [변경] 쿠폰 할인액의 결정은 쿠폰 객체가 담당합니다.
        return 3_000 if self.enabled else 0


@dataclass(frozen=True)
class Order:
    """[변경] 주문 데이터와 그 데이터를 계산하는 동작을 함께 보관합니다."""

    member_type: MemberType
    price: int
    qty: int
    coupon: Coupon

    def __post_init__(self) -> None:
        """객체가 생성될 때 주문 데이터의 유효성을 검사합니다."""
        if not isinstance(self.member_type, MemberType):
            raise TypeError("member_type은 MemberType 객체여야 합니다.")
        for name, value in (("price", self.price), ("qty", self.qty)):
            if type(value) is not int:
                raise TypeError(f"{name}은 bool을 제외한 정수여야 합니다.")
        if self.price < 0:
            raise ValueError("price는 0 이상이어야 합니다.")
        if self.qty <= 0:
            raise ValueError("qty는 1 이상이어야 합니다.")
        if not isinstance(self.coupon, Coupon):
            raise TypeError("coupon은 Coupon 객체여야 합니다.")

    @classmethod
    def from_inputs(
        cls, u_type: int, price: int, qty: int, coupon: str | bool
    ) -> "Order":
        """기존 함수와 같은 네 입력으로 주문 객체를 만드는 편의 메서드입니다."""
        return cls(
            member_type=MemberType.from_code(u_type),
            price=price,
            qty=qty,
            coupon=Coupon.from_input(coupon),
        )

    def calculate_total(self) -> int:
        """[변경] 기존 함수의 계산식을 주문 객체의 인스턴스 메서드로 옮깁니다."""
        # self로 주문에 저장된 데이터에 접근합니다. 정수 계산 규칙은 유지합니다.
        discounted_total = (
            self.price * self.qty * self.member_type.payment_percent // 100
        )
        return max(discounted_total - self.coupon.discount_amount, 0)


if __name__ == "__main__":
    # [변경] calc_order(...) 호출을 '객체 생성 → 메서드 호출'로 바꿉니다.
    order = Order.from_inputs(1, 100, 20, "yes")
    print(order.calculate_total())  # 1,900원에서 쿠폰 차감 후 최종 0원

    # 이미 객체를 사용하고 있다면 문자열 변환 없이 직접 조합할 수도 있습니다.
    another_order = Order(
        member_type=MemberType.TYPE_1,
        price=10_000,
        qty=1,
        coupon=Coupon(enabled=True),
    )
    print(another_order.calculate_total())  # 9,500 - 3,000 = 6,500원
