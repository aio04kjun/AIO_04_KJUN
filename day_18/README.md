# Streamlit 로그인 상태 유지·사용자 대화 이력 — 2~8차시

[수업 전 안내](TODAY_GUIDE.md) → [백엔드 준비](BACKEND_GUIDE.md) → [2차시](lesson02/README.md) 순서로 엽니다.

| 차시 | 교안 | 실행 코드 |
| --- | --- | --- |
| 2 | [로그인 결과 보관](lesson02/README.md) | lesson02/main.py |
| 3 | [로그인·로그아웃 화면 분기](lesson03/README.md) | lesson03/main.py |
| 4 | [내 대화 이력 바인딩](lesson04/README.md) | lesson04/main.py |
| 5 | [대화 ID 선택](lesson05/README.md) | lesson05/main.py |
| 6 | [저장 성공 후 재조회](lesson06/README.md) | lesson06/main.py |
| 7 | [만료·장애 처리](lesson07/README.md) | lesson07/main.py |
| 8 | [두 계정 통합 검증](lesson08/README.md) | lesson08/main.py |

각 차시의 전체 코드는 해당 main.py 한 개에 있습니다. backend/main.py는 차시 전체에서 함께 쓰는 실제 서비스이며 한 번만 실행합니다. 1차시 자료는 포함하지 않습니다. 시작 파일 경로는 `TODAY_GUIDE.md`이며 처음 실행할 UI 교안은 `lesson02/README.md`입니다.

인증·영구 기록·세션은 Supabase Auth·PostgreSQL·Redis에 실제로 연결하는 코드입니다. 제작 검증은 외부 응답 대역과 FastAPI·Streamlit 테스트 도구로 수행했으며, 실제 원격 연결·Windows 브라우저 조작은 각 안내의 절차로 확인합니다.
