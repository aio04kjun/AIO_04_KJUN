"""Hugging Face 로컬 모델을 CPU로 실행하는 FastAPI 백엔드."""
# 표준 라이브러리: 다운로드 명령 해석, 환경변수, 폴더, 서버 수명 관리.
import argparse
import os
from pathlib import Path
from contextlib import asynccontextmanager
from threading import Lock

# PyTorch는 CPU 계산, Transformers는 모델과 토크나이저를 담당한다.
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field



def read_settings():
    # 이미 설정된 프로세스 환경변수가 .env보다 우선한다. 문자열 치환은 끈다.
    load_dotenv(override=False, interpolate=False)
    values = {}
    for key in ("HF_MODEL_ID", "MODEL_DIR"):
        value = os.getenv(key)
        if value is None or not value.strip():
            raise ValueError(f"{key} 설정이 필요합니다.")
        values[key] = value.strip()
    model_dir = Path(values["MODEL_DIR"]).expanduser()
    # 상대 모델 경로는 이 백엔드 main.py가 있는 폴더를 기준으로 해석한다.
    if not model_dir.is_absolute():
        model_dir = Path(__file__).resolve().parent / model_dir
    return values["HF_MODEL_ID"], model_dir.resolve()


# FastAPI가 서버 시작 시 yield 앞을, 정상 종료 시 yield 뒤를 실행한다.
@asynccontextmanager
async def lifespan(app):
    _, model_dir = read_settings()
    if not model_dir.is_dir():
        raise ValueError("모델 폴더가 없습니다. .env 경로를 확인하거나 python main.py download를 실행하세요.")
    torch.set_num_threads(4)  # CPU 계산 스레드 수. PC마다 최적값은 다르다.
    app.state.tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir), local_files_only=True,  # 모델 파일을 온라인에서 자동 보충하지 않는다.
    )
    app.state.model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        dtype=torch.float32,  # CPU용 32비트 실수. torch_dtype 대신 dtype을 사용한다.
        local_files_only=True,  # 가중치도 준비된 로컬 폴더에서만 읽는다.
    )
    app.state.model.to("cpu")  # device_map="auto"를 쓰지 않아 accelerate가 필요 없다.
    app.state.model.eval()  # dropout 등을 평가 모드로 전환한다.
    app.state.lock = Lock()  # 한 프로세스의 모델 생성 요청을 한 번에 하나로 제한한다.
    print("CPU 모델 준비 완료", flush=True)
    yield
    del app.state.model
    del app.state.tokenizer


# lifespan은 여기서 등록되며 실제 실행은 Uvicorn의 서버 시작·종료 시점이다.
app = FastAPI(title="Lesson 02 CPU backend", lifespan=lifespan)


class ChatRequest(BaseModel):
    # 알려지지 않은 필드는 거절하고, 문자열 양끝 공백을 먼저 제거한다.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    prompt: str = Field(min_length=1, max_length=500, strict=True)



def prepare_inputs(messages):
    # UI가 보낸 대화 앞에 백엔드의 고정 system 지시를 붙인다.
    full_messages = [{"role": "system", "content": "한국어로 짧고 쉬운 문장으로 답하세요."}] + messages
    inputs = app.state.tokenizer.apply_chat_template(
        full_messages,
        tokenize=True,  # 대화 형식을 적용하고 토큰 번호로 변환한다.
        add_generation_prompt=True,  # assistant가 답변을 시작할 위치를 추가한다.
        return_dict=True,  # input_ids와 attention_mask를 이름으로 받는다.
        return_tensors="pt",  # PyTorch 텐서로 받는다. 모델과 입력 모두 CPU에 둔다.
    )
    if inputs["input_ids"].shape[1] > 512:
        raise HTTPException(status_code=422, detail="입력 토큰이 512를 넘었습니다. 질문을 줄이거나 새 대화를 시작하세요.")
    return inputs


class ChatResponse(BaseModel):
    answer: str


# 등록만으로 추론하지 않는다. POST /chat 요청이 와야 FastAPI가 이 함수를 호출한다.
@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    if not app.state.lock.acquire(blocking=False):  # 기다리는 요청을 쌓지 않는다.
        raise HTTPException(status_code=503, detail="모델이 사용 중입니다. 잠시 후 다시 입력하세요.")
    try:
        inputs = prepare_inputs([{"role": "user", "content": body.prompt}])
        # eval과 별도로 역전파용 기록을 끈다. 일반 def 경로는 서버 스레드에서 실행된다.
        with torch.inference_mode():
            outputs = app.state.model.generate(
                **inputs,  # input_ids, attention_mask를 전달한다.
                max_new_tokens=96,  # 새 답변의 토큰 상한이며 글자 수가 아니다.
                do_sample=False,  # 무작위 샘플링을 끈다.
                pad_token_id=app.state.tokenizer.eos_token_id,  # 단일 입력의 패딩 ID.
            )
        input_length = inputs["input_ids"].shape[1]
        answer = app.state.tokenizer.decode(
            outputs[0][input_length:], skip_special_tokens=True,  # 질문·제어 토큰 제외.
        ).strip()
        if not answer:
            raise HTTPException(status_code=502, detail="빈 답변이 생성되었습니다.")
        return ChatResponse(answer=answer)
    except HTTPException:
        raise
    except Exception:
        # 라이브러리 오류 원문에 환경 정보가 섞일 수 있어 고정 문구로 변환한다.
        raise HTTPException(status_code=500, detail="로컬 모델 생성에 실패했습니다.") from None
    finally:
        app.state.lock.release()  # 정상·입력 오류·모델 오류 모두 다음 요청을 받게 한다.



def main():
    # 이 CLI는 모델 준비 전용이다. 서버는 python -m uvicorn main:app으로 실행한다.
    parser = argparse.ArgumentParser(description="백엔드가 사용할 로컬 모델 다운로드")
    parser.add_argument("command", choices=["download"], help="모델 파일을 다운로드하고 종료")
    parser.parse_args()  # command는 download만 허용되므로 이후는 다운로드 작업이다.
    model_id, model_dir = read_settings()
    snapshot_download(
        repo_id=model_id,  # 공개 Hugging Face 모델 저장소 ID.
        local_dir=str(model_dir),  # 세 백엔드가 재사용할 실제 모델 폴더.
        allow_patterns=[  # 필요한 형식만 받아 다른 대용량 변환본은 제외한다.
            "config.json", "generation_config.json", "tokenizer*.json",
            "vocab.json", "merges.txt", "*.safetensors", "README.md", "LICENSE*",
        ],
    )
    print("다운로드 완료. Uvicorn으로 백엔드를 실행하세요.")


if __name__ == "__main__":
    main()