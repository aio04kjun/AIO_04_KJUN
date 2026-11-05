
from pathlib import Path
from huggingface_hub import snapshot_download


# Hugging Face 모델 저장소
MODEL_ID = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

# 프로젝트 경로
BASE_DIR = Path(__file__).resolve().parent

# 로컬 모델 저장 경로
MODEL_DIR = BASE_DIR / "models" / "EXAONE-3.5-2.4B-Instruct"


def download_model():

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("EXAONE 모델 다운로드")
    print("=" * 60)

    print(f"모델 ID   : {MODEL_ID}")
    print(f"저장 경로 : {MODEL_DIR}")

    try:

        # Hugging Face 공식 다운로드 API
        downloaded_path = snapshot_download(
            repo_id=MODEL_ID,
            local_dir=str(MODEL_DIR),
            resume_download=True
        )

        print("\n모델 다운로드 완료!")
        print(f"다운로드 위치: {downloaded_path}")

        # 주요 파일 확인
        required_files = [
            "config.json",
            "tokenizer_config.json"
        ]

        for filename in required_files:

            file_path = MODEL_DIR / filename

            if file_path.exists():
                print(f"[OK] {filename}")
            else:
                print(f"[확인 필요] {filename}")

        # 모델 가중치 확인
        weight_files = list(MODEL_DIR.glob("*.safetensors"))

        print(f"\n모델 가중치 파일: {len(weight_files)}개")

        if not weight_files:
            print("경고: safetensors 가중치 파일을 찾을 수 없습니다.")

    except Exception as e:

        print("\n모델 다운로드 실패")
        print(f"오류 내용: {e}")

        raise


if __name__ == "__main__":
    download_model()
