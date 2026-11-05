3. 처음부터 설치하는 순서
① Python 3.12 설치

현재 사용 중인 Python 3.13.12는 그대로 두고 Python 3.12를 추가 설치하면 됩니다.

공식 다운로드: Python 다운로드

Windows 64-bit 설치 파일을 선택하고 설치 시 Python Launcher도 사용할 수 있도록 합니다.

설치 확인:
py -3.12 --version


② ZIP 압축 해제

예를 들어 다음 경로에 압축을 해제합니다.
C:\AI4\Day17\EXAONE_CPU


③ PowerShell 실행

압축을 푼 폴더에서 PowerShell을 실행합니다.

스크립트 실행이 차단되면 다음 명령을 먼저 입력합니다.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass


④ 전체 설치 실행
.\setup.ps1


이 명령 하나로 다음 작업이 진행됩니다.
1. 기존 패키지 전용 .venv-exaone 가상환경 삭제
2. Python 3.12 기반 가상환경 생성
3. PyTorch 2.6.0 CPU 버전 다운로드 및 설치
4. 나머지 라이브러리 고정 버전 설치
5. Transformers API 호환성 검증
6. 공식 EXAONE 모델 다운로드
모델은 다음 위치에 저장됩니다.
models
 └─ EXAONE-3.5-2.4B-Instruct


⑤ 모델 실행

설치 완료 후:
.\.venv-exaone\Scripts\Activate.ps1

python main.py


4. 설치 완료 후 확인할 버전
verify_env.py 실행 결과가 다음과 같은 형태여야 합니다.
Python       : 3.12.x
PyTorch      : 2.6.0+cpu
CUDA 사용    : False
Transformers : 4.57.1
Tokenizers   : 0.22.1

환경 검증 성공


특히 create_causal_mask의 인자에 input_embeds와 cache_position이 표시되는지 확인합니다.

5. CPU 실행 시 참고사항
EXAONE 3.5 2.4B 모델을 FP32로 실행하면 모델 가중치만으로도 약 8.5GB 이상의 메모리가 필요합니다. 실제 실행에는 추가 RAM도 필요합니다.

따라서 RAM이 16GB인 PC에서는 메모리 부족이 발생할 수 있으며, 32GB 이상을 권장합니다.

이번 패키지의 핵심은 모델 파일을 직접 수정하지 않고 Transformers 4.57.1을 사용해 API 호환성을 맞추는 것입니다.

설치 후에도 오류가 발생한다면 verify_env.py 결과와 전체 오류 메시지를 보내주세요. 특히 모델 코드의 다른 API 의존성까지 확인해서 해결하겠습니다.