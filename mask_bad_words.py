import re


def mask_bad_words(chat_message: str, bad_words: list[str]) -> str:
    # 빈 금지어는 제외하고, 중복된 금지어는 하나만 남깁니다.
    words = sorted(set(word for word in bad_words if word), key=len, reverse=True)

    # 금지어가 없으면 원본 메시지를 그대로 반환합니다.
    if not words:
        return chat_message

    # 긴 단어부터 찾습니다. escape는 '.', '+' 등을 일반 문자로 취급하게 합니다.
    pattern = "|".join(re.escape(word) for word in words)

    # IGNORECASE는 대소문자를 무시하고, 찾은 문자열 길이만큼 '*'로 바꿉니다.
    # 매칭되지 않은 공백, 문장 부호, 줄바꿈 등은 그대로 유지됩니다.
    return re.sub(pattern, lambda match: "*" * len(match.group(0)),
                  chat_message, flags=re.IGNORECASE)


if __name__ == "__main__":
    # 한글 금지어 및 여러 금지어
    assert mask_bad_words("너는 바보야!", ["바보"]) == "너는 **야!"
    assert mask_bad_words("바보 멍청이", ["바보", "멍청이"]) == "** ***"

    # 대소문자 무시 및 반복 등장
    assert mask_bad_words("BAD Bad bad", ["bad"]) == "*** *** ***"
    assert mask_bad_words("bad", ["BAD"]) == "***"
    assert mask_bad_words("바보바보", ["바보"]) == "****"

    # 문장 구조 보존 및 단어 안의 부분 문자열도 마스킹
    assert mask_bad_words("Hi, BAD!\n  bye.", ["bad"]) == "Hi, ***!\n  bye."
    assert mask_bad_words("badminton", ["bad"]) == "***minton"

    # 빈 입력, 빈 목록, 빈 금지어, 금지어가 없는 메시지
    assert mask_bad_words("", ["bad"]) == ""
    assert mask_bad_words("안녕하세요", []) == "안녕하세요"
    assert mask_bad_words("abc", [""]) == "abc"
    assert mask_bad_words("bad", ["", "bad"]) == "***"
    assert mask_bad_words("좋은 하루!", ["바보"]) == "좋은 하루!"

    # 중복 금지어, 긴 금지어 우선, 정규식 특수문자
    assert mask_bad_words("bad", ["bad", "bad"]) == "***"
    assert mask_bad_words("badword", ["bad", "badword"]) == "*******"
    assert mask_bad_words("a.b aXb C++", ["a.b", "C++"]) == "*** aXb ***"

    print("15개 assert 테스트 통과")
