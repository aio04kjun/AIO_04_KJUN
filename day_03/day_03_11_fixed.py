import math  # 추가: NaN과 무한대를 검사하는 표준 라이브러리입니다.


# [원본 코드의 문제점 분석]
# 1. row["score"]: score 키가 없으면 KeyError가 발생합니다.
#    row가 None 또는 리스트여도 TypeError가 발생하며, 오류 행 번호를 알기 어렵습니다.
# 2. float(...): None, 빈 문자열, "abc"는 숫자로 바꿀 수 없어 예외가 발생합니다.
#    매우 큰 정수도 실수로 변환할 때 OverflowError가 발생할 수 있습니다.
# 3. True/False는 float()에서 1.0/0.0이 됩니다. 점수 오류를 놓칠 수 있습니다.
# 4. "nan", "inf"는 float()에서 변환에 성공합니다. round()로도 제거되지 않아
#    결과에 NaN 또는 무한대가 남습니다. 별도 검사가 필요합니다.
# 5. 원본은 잘못된 값이 어느 행에 있는지 안내하지 않아 입력 수정이 어렵습니다.
#
# [수정 기준]
# - 입력은 {"score": 숫자 또는 숫자 문자열} 형태의 행을 순회할 수 있어야 합니다.
# - 잘못된 행은 임의로 삭제하거나 0점으로 바꾸지 않고, 행 번호와 함께 알립니다.
# - 100으로 나누고 소수점 넷째 자리까지 반올림하는 계산은 유지합니다.
# - 점수 범위가 명시되지 않았으므로 음수나 100점 초과 값은 제한하지 않습니다.
# - round()는 반올림이며, 출력 형식을 0.8000처럼 네 자리로 고정하지는 않습니다.




def preprocess_legacy(data):
    res = []
    for index, row in enumerate(data, start=1):  # 수정: 오류를 안내할 행 번호를 구합니다.
        try:  # 추가: 키 누락, 잘못된 행, 숫자 변환 실패를 한곳에서 처리합니다.
            value = row["score"]  # 수정: 변환 전에 원래 값을 확인합니다.
            if isinstance(value, bool):  # 추가: True/False가 점수로 처리되지 않게 합니다.
                raise ValueError("불리언은 점수로 사용할 수 없습니다.")  # 추가
            score = float(value)  # 수정: 확인한 값을 실수로 변환합니다.
        except (KeyError, TypeError, ValueError, OverflowError) as error:  # 추가
            # 추가: 문제 행 번호를 알려주고 원래 예외도 보존합니다.
            raise ValueError(f"{index}번째 행: score에 올바른 숫자를 입력하세요.") from error

        if not math.isfinite(score):  # 추가: NaN과 양수/음수 무한대를 거부합니다.
            raise ValueError(f"{index}번째 행: NaN이나 무한대는 점수로 사용할 수 없습니다.")  # 추가
        res.append(round(score / 100.0, 4))
    return res

data = [{"score": 80}, {"score": "95.55"}, {"score": 100}]
print(preprocess_legacy(data))


# 추가: 이 파일을 직접 실행할 때만 정상 입력과 오류 입력의 결과를 보여줍니다.
# if __name__ == "__main__":
#     print("정상 입력:", preprocess_legacy([{"score": 80}, {"score": "95.55"}]))
#     print("빈 입력:", preprocess_legacy([]))
#     for bad_row in [{}, {"score": "abc"}, {"score": True}, {"score": "nan"}]:
#         try:
#             preprocess_legacy([{"score": 80}, bad_row])
#         except ValueError as error:
#             print("오류 입력:", error)
