"""3차시: UI가 보낸 대화 목록으로 모델 요청을 만든다."""
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, OpenAI
from pydantic import BaseModel, ConfigDict, Field, model_validator

load_dotenv(".env", override=False, interpolate=False)
app = FastAPI(title="멀티턴 요청 전달")


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=1000)
    history: list[Message] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def check_pairs(self):
        expected = ["user", "assistant"] * (len(self.history) // 2)
        if [m.role for m in self.history] != expected:
            raise ValueError("이력은 질문과 답변의 쌍이어야 합니다.")
        return self

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
for name, value in {"LLM_BASE_URL": LLM_BASE_URL, "LLM_MODEL": LLM_MODEL,
                    "LLM_API_KEY": LLM_API_KEY}.items():
    if not value.strip():
        raise RuntimeError(f".env의 {name} 값을 입력하세요.")
if not LLM_BASE_URL.startswith(("http://", "https://")):
    raise RuntimeError("LLM_BASE_URL 주소를 확인하세요.")

SYSTEM_MESSAGE = {"role": "system", "content": "한국어로 두 문장 안에서 답하세요. 대화에 나온 정보를 사용하고 모르는 개인 정보는 모른다고 말하세요."}


def generate_answer(messages):
    # 모델 키는 백엔드에서만 읽고 브라우저로 전달하지 않는다.
    try:
        with OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY,
                    timeout=120.0, max_retries=0) as client:
            result = client.chat.completions.create(
                model=LLM_MODEL, messages=messages,
            )
    except (APIConnectionError, APIStatusError):
        raise HTTPException(502, "모델 API 연결과 모델 이름을 확인하세요.") from None
    answer = result.choices[0].message.content if result.choices else None
    if not answer or not answer.strip():
        raise HTTPException(502, "모델에서 비어 있는 답변을 받았습니다.")
    return answer.strip()[:1000]  # 이 실습의 답변 보관 길이는 최대 1000자다.

def build_messages(history, question):
    current = [{"role": "user", "content": question}]
    return [SYSTEM_MESSAGE] + history + current

@app.post("/chat")
def chat(body: ChatInput):
    history = [m.model_dump() for m in body.history]
    messages = build_messages(history, body.question)
    answer = generate_answer(messages)
    return {"answer": answer, "context_messages": messages,
            "previous_count": len(history)}
