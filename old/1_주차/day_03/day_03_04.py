class ModelConfig:
    def __init__(self, model_name: str, learning_rate: float, epochs: int):
        self.model_name = model_name
        self.__learning_rate = 0.001
        self.__learning_rate = learning_rate
        self.epochs

    @property
    def learning_rate(self) -> float:
        return self.__learning_rate

    @learning_rate.setter
    def learning_rate(self, value: float) -> None:
        if not (0.0 < value <= 1.0):
            print(f"[검증경고] 비정상 학습률 ({value}) 감지! 기존 안전값({self.__learning_rate})을 유지합니다.")
            return
        self.__learning_rate = value

    def __str__(self) -> str:
        return f"ModelConfig(name='{self.model_name}', lr={self.learning_rate}, epochs={self.epochs})"

cfg = ModelConfig("ResNet-50", 0.01, 30)
print(cfg)
cfg.learning_rate = 5.0
print(cfg)          