"""입력 검증과 정수 금액 계산을 적용한 주문 금액 계산 예제."""

# [수정] 회원 유형과 할인 정책을 한곳에서 확인할 수 있도록 상수로 분리합니다.
# 0은 비회원이며, 값은 할인 후 지불할 금액의 백분율입니다.
PAYMENT_PERCENT_BY_USER_TYPE = {0: 100, 1: 95, 2: 90, 3: 80}
COUPON_DISCOUNT = 3_000


def calc_order(u_type: int, price: int, qty: int, coupon: str | bool) -> int:
    """회원 할인 후 쿠폰을 차감한 최종 금액을 원 단위 정수로 반환합니다.

    u_type: 0(비회원), 1(5% 할인), 2(10% 할인), 3(20% 할인).
    price: 0 이상의 정수 가격(원). qty: 1 이상의 정수 수량.
    coupon: YES/NO 문자열(대소문자 및 앞뒤 공백 무시) 또는 bool.
    회원 할인 금액의 1원 미만은 버리고, 최종 금액은 0원 이상으로 제한합니다.
    잘못된 타입은 TypeError, 허용 범위를 벗어난 값은 ValueError를 발생시킵니다.
    """
    # [수정] bool은 int의 하위 타입이므로 정확한 타입을 검사하여 제외합니다.
    for name, value in (("u_type", u_type), ("price", price), ("qty", qty)):
        if type(value) is not int:
            raise TypeError(f"{name}은 bool을 제외한 정수여야 합니다.")

    # [수정] 잘못된 입력을 무할인 또는 0원 주문으로 숨기지 않고 거부합니다.
    if u_type not in PAYMENT_PERCENT_BY_USER_TYPE:
        raise ValueError("u_type은 0, 1, 2, 3 중 하나여야 합니다.")
    if price < 0:
        raise ValueError("price는 0 이상이어야 합니다.")
    if qty <= 0:
        raise ValueError("qty는 1 이상이어야 합니다.")

    # [수정] 'yes'도 인식하되, 오타를 쿠폰 미사용으로 조용히 처리하지 않습니다.
    # bool('NO')도 True가 되므로 문자열을 bool()로 직접 변환하지 않습니다.
    if isinstance(coupon, bool):
        use_coupon = coupon
    elif isinstance(coupon, str):
        normalized_coupon = coupon.strip().upper()
        if normalized_coupon not in ("YES", "NO"):
            raise ValueError("coupon 문자열은 YES 또는 NO여야 합니다.")
        use_coupon = normalized_coupon == "YES"
    else:
        raise TypeError("coupon은 YES/NO 문자열 또는 bool이어야 합니다.")

    # [수정] float 대신 정수 비율과 //를 사용하여 오차 없이 원 미만을 버립니다.
    # 계산 순서는 기존 정책과 동일하게 '회원 할인 → 쿠폰 차감'입니다.
    total = price * qty * PAYMENT_PERCENT_BY_USER_TYPE[u_type] // 100
    if use_coupon:
        total -= COUPON_DISCOUNT
    return max(total, 0)


# [수정] 다른 파일에서 import할 때 예제 계산과 출력이 실행되지 않게 합니다.
if __name__ == "__main__":
    result = calc_order(1, 100, 20, "yes")
    print(result)  # 2,000원 → 회원 할인 1,900원 → 쿠폰 차감 → 최종 0원
