# 실행하고 상품 구매 흐름 확인하기

[프로젝트 안내](../README.md) · [화면·기능 안내](frontend.md) · [API 명세](api-spec.md)

## 가장 빠른 확인 — 로컬 체험 모드

현재 작업 PC에는 필요한 Python 의존성이 있으므로 VSCode 터미널(PowerShell)에서 다음 명령으로 실행할 수 있습니다.

```powershell
cd C:\AIO_04_kjun\shopping-mall
.\start.ps1 -Demo
```

브라우저에서 [http://localhost:8000](http://localhost:8000)을 엽니다. 터미널은 실행 상태로 유지하고, 종료할 때 Ctrl+C를 누릅니다.

| 로그인 정보 | 값 |
|---|---|
| 이메일 | demo@orbit.local |
| 비밀번호 | Orbit1234! |

로그인 화면의 **체험 계정 입력** 버튼도 사용할 수 있습니다. 체험 모드는 화면 상단에 표시됩니다. 회원가입·장바구니·주문·구매 내역을 로컬 메모리에서 처리하며, 실제 Supabase나 결제 서버에 연결하지 않습니다. 서버를 재시작하면 체험 데이터가 모두 초기화됩니다. 실제 개인정보 대신 예제 이름·연락처·주소를 입력하세요.

다른 포트를 사용하려면 다음과 같이 실행합니다.

```powershell
.\start.ps1 -Demo -Port 8001
```

이 경우 [http://localhost:8001](http://localhost:8001)을 엽니다. 체험 모드는 앱 출처도 해당 포트로 자동 설정합니다.

start.ps1은 프로젝트 가상환경 → 설치된 Python → 이 PC의 Codex 번들 Python 순서로 사용 가능한 실행 환경을 찾습니다. 번들 Python을 사용할 때만 작업공간의 `.supabase-deps`를 임시 참조합니다. 패키지를 자동 설치하거나 시스템 설정을 바꾸지는 않습니다. `-Check` 옵션은 의존성만 확인합니다.

## 다른 PC 또는 새 환경에서 준비

Python 3.12 이상을 설치한 뒤 shopping-mall 폴더에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py --demo
```

PowerShell에서 ps1 실행이 제한되어 있다면 위의 Python 직접 실행 명령을 사용해도 됩니다. Node.js·npm·프론트엔드 빌드는 필요하지 않습니다. HTML 파일을 직접 더블클릭하거나 Live Server로 열지 말고 FastAPI 서버 주소로 접속하세요.

## 구매 절차를 확인하는 순서

1. 로그인하지 않은 상태에서 **데일리 머그컵**을 선택합니다.
2. 수량을 2개로 바꾸고 **장바구니 담기**를 누릅니다.
3. 로그인 화면으로 이동하며 원래 상품·수량이 next에 보존됩니다.
4. 체험 계정으로 로그인하면 원래 상품 화면으로 돌아오고, 선택한 2개를 한 번 담습니다.
5. **장바구니로 이동**을 누르고 수량·합계 24,000원을 확인합니다.
6. **선택 상품 주문하기**를 누릅니다.
7. 연락처 `010-0000-0000`, 주소 `01234 테스트시 예제로 1, 101호` 등 예제 배송정보를 입력합니다.
8. 모의 결제 동의 체크 후 **24,000원 모의 결제**를 누릅니다.
9. 완료 안내와 함께 상품 목록으로 이동합니다.
10. **마이페이지 → 구매 내역 → 주문 상세**에서 상품·수량·구매 단가·결제 결과를 확인합니다.

바로 구매를 누르면 장바구니를 거치지 않고 주문 화면으로 이동합니다. 비로그인 상태라면 먼저 로그인하며, 로그인 후 주문 화면으로 돌아옵니다. 로그인만으로 주문이나 결제를 자동 실행하지 않습니다.

결제 후에도 장바구니 항목은 유지됩니다. 메모 노트는 품절 예제이므로 구매 버튼이 비활성화됩니다. 회원정보 수정은 이름·연락처를 바꾸는 기능이며, 탈퇴는 현재 비밀번호와 동의 확인 후 처리합니다.

## 실제 Supabase와 연결

체험 서버가 실행 중이면 Ctrl+C로 종료합니다.

1. 신규 개발용 Supabase 프로젝트에서 [schema.sql](../sql/schema.sql) → [seed.sql](../sql/seed.sql) → [backend-functions.sql](../sql/backend-functions.sql) 순서로 실행합니다. 이미 수정된 6개 테이블을 설치했다면 스키마를 재실행하지 않고 빠진 함수만 설치합니다.
2. 아래 명령으로 예제 환경변수 파일을 복사합니다. 이미 .env가 있다면 덮어쓰지 말고 내용을 확인합니다.

```powershell
Copy-Item .env.example .env
```

3. .env에 프로젝트 URL·공개 키·서버 비밀키를 입력하고 다음 값을 설정합니다.

```dotenv
SHOP_DEMO=false
APP_ORIGIN=http://localhost:8000
COOKIE_SECURE=false
ENABLE_MOCK_PAYMENTS=true
```

4. 실행합니다.

```powershell
.\start.ps1
```

또는 가상환경 Python으로 직접 실행합니다.

```powershell
.\.venv\Scripts\python.exe run.py
```

.env 로딩에는 requirements.txt의 python-dotenv가 필요합니다. 서버 환경변수를 직접 설정한 경우 .env 없이도 실행할 수 있습니다.

5. Supabase Auth 이메일·비밀번호 가입을 활성화합니다. 개발용 Site URL과 허용 Redirect URL에 `http://localhost:8000/login`을 설정합니다. 이메일 인증이 켜져 있으면 가입 후 메일의 인증을 완료하고 로그인합니다. 이 UI는 인증 링크의 토큰을 직접 저장하지 않으며 비밀번호 로그인을 사용합니다.

**Supabase 연결 모드에서는 실제 계정·장바구니·주문을 DB에 저장합니다.** 결제는 여전히 모의 결제입니다. 실제 PG 결제나 실제 상품 발송은 수행하지 않습니다. 서버 비밀키는 브라우저 코드나 Git에 넣지 않습니다.

## 자주 생기는 문제

| 증상 | 확인할 내용 |
|---|---|
| 8000 포트 사용 중 | 이미 실행 중인 서버를 사용하거나 -Port 8001로 실행 |
| Python 의존성 없음 | 가상환경을 만들고 requirements.txt 설치 |
| 실연결에서 환경변수 누락 | .env 경로가 shopping-mall/.env인지 확인 |
| CSRF_FAILED | localhost와 127.0.0.1을 섞지 않고 APP_ORIGIN과 동일한 주소 사용 |
| 로컬에서 로그인 쿠키가 저장되지 않음 | HTTP 개발 환경의 COOKIE_SECURE=false 확인 |
| 상품 요청이 실패함 | 프로젝트 URL·공개 키·SQL 설치 상태 확인 |
| add_cart_item 함수를 찾지 못함 | backend-functions.sql 실행 |
| 실연결에서 로그인 거부 | 비밀번호·이메일 인증 완료 여부 확인 |
| 체험 데이터가 사라짐 | 서버 메모리 데이터이므로 재시작·reload 시 초기화되는 정상 동작 |

## 검증 및 범위

자동 테스트는 다음 명령으로 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

53개 테스트가 통과했습니다. 로컬 체험 환경의 실제 브라우저에서 로그인 복귀·장바구니·배송 입력·모의 결제·상품 목록 이동·구매 내역까지 확인했습니다. 이후 실제 Supabase DB에 SQL 설치와 롤백 검증, Auth·Data API 연결, 실연결 서버의 상품 조회까지 완료했습니다. [현재 연결 상태](supabase-connection.md)처럼 실제 계정의 인증 메일·로그인 전체 흐름·동시 세션 구매·Render 배포는 추가 확인이 필요합니다.
