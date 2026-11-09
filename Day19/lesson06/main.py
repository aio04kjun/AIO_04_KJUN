import os
from uuid import uuid4

import httpx
import streamlit as st
from dotenv import load_dotenv

st.title("저장한 대화 불러오기")
load_dotenv(".env", override=False, interpolate=False)
API_BASE_URL = os.getenv("API_BASE_URL", "").strip().rstrip("/")
if not API_BASE_URL.startswith(("http://", "https://")):
    st.error(".env의 API_BASE_URL을 확인하세요.")
    st.stop()


def clear_private():
    for key in ("access_token", "user_id", "bound_user_id", "conversation_id", "selected_id",
                "messages", "last_context", "pending", "fail_next_chat", "error", "notice"):
        st.session_state.pop(key, None)


def api(method, path, payload=None):
    headers = {}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        # 현재 요청을 백엔드로 전달한다.
        response = httpx.request(method, API_BASE_URL + path,
                                 json=payload, headers=headers, timeout=150.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            clear_private()
            st.session_state["notice"] = "로그인이 필요합니다. 이메일과 비밀번호를 확인하세요."
            st.rerun()

        st.error(f"요청 실패 ({exc.response.status_code}). 백엔드와 모델 서버를 확인하세요.")
        st.stop()
    except httpx.RequestError:

        st.error("서버에 연결할 수 없습니다. 서버 CMD를 확인하세요.")
        st.stop()
    return response.json()





def logout():
    try:
        httpx.post(API_BASE_URL + "/auth/logout", headers={
            "Authorization": "Bearer " + st.session_state.get("access_token", ""),
        }, timeout=10.0)
    except httpx.RequestError:
        pass
    clear_private()
    st.session_state["notice"] = "화면의 로그인과 선택 정보를 지웠습니다."
    st.rerun()


notice = st.session_state.pop("notice", None)
if notice:
    st.info(notice)
error = st.session_state.pop("error", None)
if error:
    st.error(error)
if not st.session_state.get("access_token"):
    with st.form("login", clear_on_submit=True):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")
    if submitted:
        if not email.strip() or not password:
            st.warning("이메일과 비밀번호를 입력하세요.")
        else:
            result = api("POST", "/auth/login", {"email": email.strip(), "password": password})
            clear_private()
            st.session_state["access_token"] = result["access_token"]
            st.rerun()
    st.stop()
if st.button("계정 바꾸기 / 로그아웃"):
    logout()
profile = api("GET", "/me")
if st.session_state.get("bound_user_id") != profile["id"]:
    for key in ("conversation_id", "selected_id", "messages", "last_context", "pending", "fail_next_chat"):
        st.session_state.pop(key, None)
    st.session_state["bound_user_id"] = profile["id"]
st.caption("현재 계정: " + (profile["email"] or profile["id"]))
st.button("화면 다시 실행")


def load_history(conversation_id):
    data = api("GET", f"/conversations/{conversation_id}/messages")
    return data[-2:]  # 시작 코드: 마지막 질문·답변만 화면에 표시한다.


with st.form("create_room", clear_on_submit=True):
    title = st.text_input("새 대화 제목", value="학습 대화")

    create = st.form_submit_button("대화 만들기")
if create:
    if not title.strip():
        st.warning("대화 제목을 입력하세요.")
    else:
        room = api("POST", "/conversations", {"title": title.strip()})
        st.session_state["selected_id"] = room["id"]
        st.session_state.pop("last_context", None)
        st.rerun()
rooms = api("GET", "/conversations")
if not rooms:
    st.info("제목을 입력하고 대화 만들기를 누르세요.")
    st.stop()
labels = {room["id"]: room["title"] + " · " + room["id"][:8] for room in rooms}
ids = list(labels)
if st.session_state.get("selected_id") not in ids:
    st.session_state["selected_id"] = ids[0]


def room_label(room_id):
    return labels[room_id]


selected_id = st.selectbox("대화 선택", ids, format_func=room_label, key="selected_id")

st.session_state["messages"] = load_history(selected_id)
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])
if "last_context" in st.session_state:
    with st.expander("직전 요청에서 AI에게 보낸 메시지"):
        st.json(st.session_state["last_context"])

question = st.chat_input("질문을 입력하세요")
if question and question.strip():
    result = api("POST", "/chat", {
        "conversation_id": selected_id, "question": question.strip(), "request_id": str(uuid4()),
    })
    st.session_state["last_context"] = result["context_messages"]
    st.session_state["notice"] = f"답변 생성 완료 · 이전 메시지 {result['previous_count']}개 포함"
    st.rerun()

