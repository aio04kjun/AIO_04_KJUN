def preprocess_legacy(data):
    res = []
    for row in data:
        score = float(row["score"])
        res.append(round(score / 100.0, 4))
    return res
