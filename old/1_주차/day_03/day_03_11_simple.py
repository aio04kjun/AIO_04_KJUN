# 추가: 각 행에 숫자 또는 숫자 문자열인 score가 있다고 가정합니다.
def scores_to_ratios(data):
    # 수정: 리스트 컴프리헨션으로 변환, 나눗셈, 반올림을 한 줄에 처리합니다.
    return [round(float(row["score"]) / 100, 4) for row in data]


# 추가: 파일을 직접 실행하면 사용 예제의 결과를 출력합니다.
if __name__ == "__main__":
    data = [{"score": 80}, {"score": "95.55555"}, {"score": 100}]
    print(scores_to_ratios(data))  # 결과: [0.8, 0.9556, 1.0]
