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
import json
from queue import Empty
from threading import Thread
from transformers import TextIteratorStreamer
from fastapi.responses import StreamingResponse
from typing import Literal
from pydantic import model_validator


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
app = FastAPI(title="Lesson 04 CPU backend", lifespan=lifespan)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]  # system 지시는 백엔드에서만 추가한다.
    content: str = Field(min_length=1, max_length=2000, strict=True)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: list[Message] = Field(min_length=1, max_length=9)  # 과거 4쌍+현재 질문까지.

    # FastAPI가 본문을 검증할 때 실행된다. user부터 번갈아 나오고 마지막은 user여야 한다.
    @model_validator(mode="after")
    def check_order(self):
        if len(self.messages) % 2 == 0:
            raise ValueError("마지막 메시지는 user 질문이어야 합니다.")
        for index, message in enumerate(self.messages):
            expected = "user" if index % 2 == 0 else "assistant"
            if message.role != expected:
                raise ValueError("user와 assistant를 번갈아 전달하세요.")
        return self



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


def encode_event(event):
    # 한 JSON 객체를 한 줄로 전송한다. 본문 속 줄바꿈은 JSON 문자열로 이스케이프된다.
    return json.dumps(event, ensure_ascii=False) + "\n"


def stream_events(streamer, worker, errors):
    has_text = False
    try:
        for text in streamer:  # 모델이 생성 중에 내놓은 실제 텍스트 조각을 받는다.
            if text:
                has_text = has_text or bool(text.strip())
                yield encode_event({"type": "delta", "text": text})
        worker.join()  # 정상 종료 신호 이후 작업 결과를 확인한다.
        if errors:
            yield encode_event({"type": "error", "message": "모델 생성에 실패했습니다."})
        elif not has_text:
            yield encode_event({"type": "error", "message": "빈 답변이 생성되었습니다."})
        else:
            yield encode_event({"type": "done"})  # 정상 완료일 때만 보낸다.
    except Empty:
        # timeout은 큐에서 다음 조각을 기다리는 제한이다. CPU 작업의 강제 취소가 아니다.
        yield encode_event({"type": "error", "message": "모델 응답 대기 시간이 초과되었습니다."})


# 현재 백엔드 버전의 스트리밍 요청만 등록한다.
@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    if not app.state.lock.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="모델이 사용 중입니다. 잠시 후 다시 입력하세요.")
    try:
        inputs = prepare_inputs([message.model_dump() for message in body.messages])
        streamer = TextIteratorStreamer(
            app.state.tokenizer,  # 같은 모델의 토크나이저로 디코딩한다.
            skip_prompt=True,  # 입력 질문·이력을 스트림에 섞지 않는다. 기본값은 False다.
            skip_special_tokens=True,  # 제어 토큰은 화면에서 숨긴다.
            timeout=180.0,  # 다음 텍스트 조각을 큐에서 기다리는 최대 시간(초).
        )
        errors = []

        def run_generation():
            try:
                # inference_mode는 스레드별 설정이므로 실제 생성 스레드 안에 둔다.
                with torch.inference_mode():
                    app.state.model.generate(
                        **inputs,
                        streamer=streamer,  # generate가 실행되는 동안 토큰을 streamer로 전달한다.
                        max_new_tokens=96,  # CPU 실습용 답변 상한.
                        do_sample=False,  # 무작위 샘플링을 끈다.
                        pad_token_id=app.state.tokenizer.eos_token_id,  # 단일 입력의 패딩 ID.
                    )
            except Exception:
                errors.append(True)  # 예외 원문 대신 실패 여부만 응답 측에 전달한다.
                # generate가 실패해도 소비자가 무기한 기다리지 않게 종료 신호를 넣는다.
                streamer.on_finalized_text("", stream_end=True)
            finally:
                app.state.lock.release()  # 생성이 끝나야 다음 모델 요청을 허용한다.

        worker = Thread(target=run_generation, daemon=True)  # 서버 종료를 막지 않는 생성 스레드.
        worker.start()  # 생성과 응답 소비를 겹쳐 실행한다. 같은 함수를 바로 호출하면 안 된다.
    except Exception:
        app.state.lock.release()  # 입력 준비 또는 스레드 시작 실패 시에만 이쪽에서 해제한다.
        raise
    return StreamingResponse(
        stream_events(streamer, worker, errors),  # 완성된 문자열 대신 반복자를 전달한다.
        media_type="application/x-ndjson",  # SSE가 아니라 줄 단위 JSON 스트림이다.
        headers={"Cache-Control": "no-cache"},  # 응답 캐시 재사용을 피한다.
    )



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
