import re


def mask_bad_words(chat_message: str, bad_words: list[str]) -> str:
    # 원본 글자를 리스트로 복사하면 원하는 위치의 글자만 바꿀 수 있습니다.
    masked_chars = list(chat_message)

    for word in bad_words:
        # 빈 문자열은 금지어로 취급하지 않습니다.
        if not word:
            continue

        # 특수문자도 글자 그대로 찾고, 영문 대소문자는 구분하지 않습니다.
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        start = 0

        while True:
            # 마스킹 결과가 아닌 원본에서 찾아야 겹치는 금지어도 찾을 수 있습니다.
            match = pattern.search(chat_message, start)
            if match is None:
                break

            # 발견한 금지어가 차지하는 위치를 글자 수만큼 별표로 바꿉니다.
            for index in range(match.start(), match.end()):
                masked_chars[index] = "*"

            # 한 글자 뒤에서 다시 찾으면 같은 금지어가 겹쳐 있어도 처리됩니다.
            start = match.start() + 1

    # 수정한 글자들을 이어 붙여 최종 문자열을 반환합니다.
    return "".join(masked_chars)


if __name__ == "__main__":
    # 입력 메시지, 금지어 목록, 예상 결과를 함께 정의합니다.
    test_cases = [
        ("너는 바보야", ["바보"], "너는 **야"),
        ("BAD Bad bad", ["bad"], "*** *** ***"),
        ("안녕, 친구!", ["바보"], "안녕, 친구!"),
        ("바보 멍청이", ["바보", "멍청이"], "** ***"),
        ("바보바보", ["바보"], "****"),
        ("바보!\n  BAD?", ["바보", "bad"], "**!\n  ***?"),
        ("", ["bad"], ""),
        ("Hello!", [], "Hello!"),
        ("Hello!", [""], "Hello!"),
        ("BAD", ["", "bad", "BAD"], "***"),
        ("a.b axb C++ [x]", ["a.b", "c++", "[x]"], "*** axb *** ***"),
        ("banana", ["ana"], "b*****"),
        ("abcde", ["abc", "cde"], "*****"),
        ("abcde", ["cde", "abc"], "*****"),
        ("badminton", ["bad"], "***minton"),
        ("안녕 😀 친구", ["😀"], "안녕 * 친구"),
        ("Straße BAD", ["bad"], "Straße ***"),
        ("Hi there", ["hi there"], "********"),
    ]

    for message, words, expected in test_cases:
        actual = mask_bad_words(message, words)
        assert actual == expected, (message, words, expected, actual)
        # 금지어를 가려도 원본 메시지의 전체 글자 수는 유지되어야 합니다.
        assert len(actual) == len(message)

    # 함수가 전달받은 금지어 목록 자체를 수정하지 않는지도 확인합니다.
    original_words = ["bad", "바보"]
    assert mask_bad_words("BAD 바보", original_words) == "*** **"
    assert original_words == ["bad", "바보"]

    print(f"{len(test_cases)} test cases passed; input list preserved.")
