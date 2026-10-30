# Render 배포 준비

[프로젝트 안내](../README.md) · [설정 파일](../render.yaml)

배포 설정만 작성했습니다. 실제 Render 서비스 생성·연결·배포는 실행하지 않았습니다.

## 설정

현재 저장소 루트 아래 `shopping-mall` 폴더가 있으므로 Render Blueprint Path에 `shopping-mall/render.yaml`을 지정합니다. YAML의 rootDir는 shopping-mall입니다. 프로젝트 폴더 자체를 별도 저장소 루트로 옮기면 rootDir도 조정해야 합니다.

| 설정 | 값 |
|---|---|
| Runtime | Python |
| Root Directory | shopping-mall |
| Build Command | pip install -r requirements.txt |
| Start Command | uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers |
| Health Check | /health |

APP_ORIGIN은 실제 HTTPS 서비스 주소로 설정하고 끝에 경로·슬래시를 붙이지 않습니다. COOKIE_SECURE=true를 사용합니다. Supabase URL·공개 키·서버 비밀키는 Render 환경변수로 입력합니다. ENABLE_MOCK_PAYMENTS=true는 모의 결제 데모용이며 실제 결제 서비스가 아닙니다.

현재 요청 제한은 단일 프로세스 메모리를 사용합니다. 임의의 X-Forwarded-For를 신뢰하지 않도록 proxy headers를 사용하지 않습니다. Render 프록시 IP를 여러 사용자가 공유하더라도 식별 조합별 제한을 적용하지만, 다중 서버 통합 제한이 필요하면 별도 게이트웨이 정책을 추가해야 합니다.

Supabase의 Site URL·허용 이메일 Redirect URL을 실제 서비스의 `/login` 경로로 설정합니다. Step 3의 HTML·API를 같은 FastAPI 서버에서 제공합니다. SHOP_DEMO=false를 유지하고 실제 프로젝트의 이메일 인증과 브라우저 전체 흐름을 검증한 뒤 배포합니다.

## 배포 전 확인

SQL 설치 순서, API 키 종류, HTTPS 쿠키, 실제 인증 메일, RLS, 재고 동시 구매를 개발 프로젝트에서 검증해야 합니다. health는 프로세스 생존 확인이며 데이터베이스 연결 상태를 검사하지 않습니다.

설정 근거: [Render FastAPI 배포](https://render.com/docs/deploy-fastapi), [Blueprint 경로](https://render.com/docs/infrastructure-as-code), [Blueprint 명세](https://render.com/docs/blueprint-spec).
