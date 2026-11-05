# 다운로드받은 모델의 modeling_exaone.py 파일에서
# causal_mask = create_causal_mask( 를 찾아서
# 두번째 매개변수를 input_embeds=inputs_embeds, 변경


import torch
import traceback
import time

from pathlib import Path
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextStreamer
)


# ==================================================
# 1. 모델 설정
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = (
    BASE_DIR
    / "models"
    / "EXAONE-3.5-2.4B-Instruct"
)

DEVICE = torch.device("cpu")

# CPU 스레드 설정
CPU_THREADS = 4

torch.set_num_threads(CPU_THREADS)

try:
    torch.set_num_interop_threads(2)
except RuntimeError:
    pass

# 생성 설정
MAX_NEW_TOKENS = 64

# KV Cache 사용
USE_CACHE = True


# ==================================================
# 2. 모델 로딩
# ==================================================

def load_model():

    print("=" * 60)
    print("EXAONE 3.5 모델 로딩")
    print("=" * 60)

    start_time = time.perf_counter()

    # 모델 경로 확인
    if not MODEL_DIR.exists():

        raise FileNotFoundError(
            f"모델 경로가 존재하지 않습니다.\n"
            f"{MODEL_DIR}\n"
            "먼저 download_model.py를 실행하세요."
        )

    print(f"실행 장치 : {DEVICE}")
    print(f"모델 경로 : {MODEL_DIR}")
    print(f"CPU 스레드: {CPU_THREADS}")

    # --------------------------------------------------
    # Tokenizer 로딩
    # --------------------------------------------------

    print("\n[1] Tokenizer 로딩")

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_DIR),
        trust_remote_code=True,
        local_files_only=True
    )

    # --------------------------------------------------
    # Model 로딩
    # --------------------------------------------------

    print("\n[2] Model 로딩")

    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR),
        dtype=torch.float32,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        local_files_only=True
    )

    # CPU 지정
    model.to(DEVICE)

    # 평가 모드
    model.eval()

    elapsed = time.perf_counter() - start_time

    print("\n[3] 모델 로딩 완료")
    print(f"모델 타입 : {model.dtype}")
    print(f"실행 장치 : {model.device}")
    print(f"로딩 시간 : {elapsed:.2f}초")

    return model, tokenizer


# ==================================================
# 3. 질문 및 답변
# ==================================================

def chat(model, tokenizer, question):

    # --------------------------------------------------
    # 대화 메시지
    # --------------------------------------------------

    messages = [
        {
            "role": "system",
            "content": (
                "You are EXAONE, a helpful AI assistant "
                "developed by LG AI Research. "
                "Answer in Korean clearly and accurately. "
                "Provide useful explanations with relevant details. "
                "If information is uncertain, explain the uncertainty."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]

    # --------------------------------------------------
    # Chat Template
    # --------------------------------------------------

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True
    )

    # CPU 입력
    inputs = inputs.to(DEVICE)

    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]

    input_length = input_ids.shape[-1]

    print(f"토큰 입력 길이: {input_length}")

    # --------------------------------------------------
    # 실시간 출력 설정
    # --------------------------------------------------

    streamer = TextStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True
    )

    # --------------------------------------------------
    # 답변 생성
    # --------------------------------------------------

    start_time = time.perf_counter()

    print("\n[EXAONE 답변]")
    print("-" * 50)

    try:

        with torch.inference_mode():

            output = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,

                max_new_tokens=MAX_NEW_TOKENS,

                do_sample=False,

                use_cache=USE_CACHE,

                pad_token_id=tokenizer.eos_token_id,

                streamer=streamer
            )

        elapsed = time.perf_counter() - start_time

        # 생성된 토큰 추출
        generated_tokens = output[
            0, input_length:
        ]

        # 답변 문자열
        answer = tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        )

        print("\n")
        print("-" * 50)

        print(f"생성 토큰 수: {len(generated_tokens)}")
        print(f"생성 소요 시간: {elapsed:.2f}초")

        if elapsed > 0:
            print(
                f"초당 생성 토큰: "
                f"{len(generated_tokens) / elapsed:.2f}"
            )

        return answer.strip()

    except Exception:

        print("\n답변 생성 중 오류 발생")
        traceback.print_exc()

        raise


# ==================================================
# 4. 프로그램 실행
# ==================================================

def main():

    try:

        model, tokenizer = load_model()

    except Exception:

        print("\n모델 로딩 실패")
        traceback.print_exc()

        return

    print("\n" + "=" * 60)
    print("EXAONE 3.5 한국어 대화 테스트")
    print("종료하려면 exit 입력")
    print("=" * 60)

    while True:

        try:

            question = input("\n질문: ").strip()

            if question.lower() in ("exit", "quit"):

                print("프로그램을 종료합니다.")
                break

            if not question:
                continue

            print("\n답변 생성 중...")

            answer = chat(
                model,
                tokenizer,
                question
            )

        except KeyboardInterrupt:

            print("\n프로그램을 종료합니다.")
            break

        except Exception as e:

            print("\n오류 유형:", type(e).__name__)
            print("오류 내용:", repr(e))


# ==================================================
# 5. Entry Point
# ==================================================

if __name__ == "__main__":

    main()