import argparse
import json


def calculate_even_sum_and_count(n: int) -> dict[str, int]:
    """1부터 n까지의 짝수 합과 개수를 반환한다."""
    even_sum = 0
    even_count = 0

    if n < 1:
        return {"Sum": 0, "Count": 0}

    for i in range(1, n + 1):
        if i % 2 == 0:
            even_sum += i
            even_count += 1

    return {"Sum": even_sum, "Count": even_count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="1부터 n까지의 짝수 합과 개수 계산")
    parser.add_argument("n", type=int, help="범위의 마지막 정수")
    args = parser.parse_args()
    print(json.dumps(calculate_even_sum_and_count(args.n)))
    assert calculate_even_sum_and_count(100) == {"sum": 2550, "count": 50}, "Test 1 Failed"
    assert calculate_even_sum_and_count(1) == {"sum": 0, "count": 0}, "Test 2 Failed"
    assert calculate_even_sum_and_count(-5) == {"sum": 0, "count": 0}, "Test 3 Failed"
    print("모든 테스트 케이스가 성공했습니다.")
