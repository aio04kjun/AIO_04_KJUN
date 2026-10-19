class DigitalWallet:
    def __init__(self, owner: str, initial_balance: int = 0):
        self.owner = owner
        self.__balance = 0
        self.balance = initial_balance # setter 검문소를 거쳐 안전하게 초기화
   
    @property
    def balance(self) -> int:
        print("balance 출력 호줄")
        return self.__balance
    
    @balance.setter
    def balance(self, amount: int) -> None:
        print("balance 세팅 호줄")
        if amount < 0:
            print(f"[보안 경고] 잔액은 음수가 될 수 없습니다! (입력값: {amount}원 -> 거부됨)")
            return
        self.__balance = amount

    def deposit(self, amount: int) -> str:
        if amount <= 0:
            return "[오류] 입금액은 0원보다 커야 합니다."
        self.balance += amount
        return f"[{self.owner}] {amount:,}원 입금 완료 (현재 잔액: {self.balance:,}원)"


wallet = DigitalWallet("이코딩", 10000)
print(wallet.deposit(5000))
wallet.balance = -99999 # 외부에서 불법 음수 대입 시도 -> setter가 즉시 차단!
print(f"최종 안전 잔액: {wallet.balance:,}원")

