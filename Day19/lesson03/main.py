"""3차시: 대화 목록과 질문을 FastAPI로 보낸다."""
import os

import httpx
import streamlit as st
from dotenv import load_dotenv

st.title("FastAPI로 이어가는 대화")
load_dotenv(".env", override=False, interpolate=False)
API_BASE_URL = os.getenv("API_BASE_URL", "").strip().rstrip("/")
if not API_BASE_URL.startswith(("http://", "https://")):
    st.error(".env의 API_BASE_URL을 확인하세요.")
    st.stop()
if "messages" not in st.session_state:
    st.session_state["messages"] = []


def make_payload(history, question):
    # 시작 코드: 화면 기록은 있지만 요청 본문에는 빈 목록을 넣는다.
    return {"question": question, "history": []}


st.button("화면 다시 실행")
if st.button("새 대화"):
    st.session_state["messages"] = []
    st.session_state.pop("last_context", None)
    st.rerun()
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])
if "last_context" in st.session_state:
    with st.expander("직전 요청에서 AI에게 보낸 메시지"):
        st.json(st.session_state["last_context"])
question = st.chat_input("질문을 입력하세요")
if question and question.strip():
    question = question.strip()
    if len(question) > 1000:
        st.warning("질문은 1000자 이내로 입력하세요.")
        st.stop()
    payload = make_payload(st.session_state["messages"], question)
    try:
        response = httpx.post(API_BASE_URL + "/chat", json=payload, timeout=150.0)
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPError:
        st.error("FastAPI와 모델 API 상태를 확인하고 다시 입력하세요.")
        st.stop()
    st.session_state["last_context"] = result["context_messages"]
    st.session_state["messages"].extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": result["answer"]},
    ])
    st.rerun()
