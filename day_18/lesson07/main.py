"""7차시: 로그인 만료와 서버 장애를 구분하기"""
# 환경변수는 .env 로드 후 조회한다. 실제 값은 화면이나 로그에 출력하지 않는다.
import os
import httpx
import streamlit as st
from dotenv import load_dotenv
from uuid import uuid4  # 미확정 저장 한 건의 요청 ID 생성.
load_dotenv(".env", override=False, interpolate=False)  # 현재 폴더·기존 환경 우선·문자열 치환 끔.
API_BASE_URL = os.getenv("API_BASE_URL", "").strip().rstrip("/")
if not API_BASE_URL or not API_BASE_URL.startswith(("http://", "https://")):
    st.error("API_BASE_URL 설정을 확인하세요.")
    st.stop()  # 이후 API 요청을 실행하지 않는다. 서버 프로세스 종료가 아니다.

# 첫 실행에서만 각 보관함을 만든다. 이미 있는 값을 재실행 때 덮어쓰지 않는다.
if "access_token" not in st.session_state:
    st.session_state["access_token"] = ""
if "user" not in st.session_state:
    st.session_state["user"] = None
if "pending" not in st.session_state:
    st.session_state["pending"] = None


def clear_private():
    # 현재 차시에서 사용하는 개인 상태만 지운다. 전체 세션을 무조건 clear하지 않는다.
    for key in ('access_token', 'user', 'conversations', 'selected_id', 'messages', 'pending'):
        st.session_state.pop(key, None)  # 없는 키도 오류 없이 처리한다.


def api(method, path, payload=None):
    # UI 서버가 백엔드를 호출한다. 브라우저에서 직접 DB에 연결하지 않는다.
    headers = {}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        response = httpx.request(
            method, API_BASE_URL + path,
            json=payload,  # dict를 JSON 요청 본문으로 변환한다. GET에서는 None이다.
            headers=headers,  # 현재 세션의 토큰만 담는다.
            timeout=15.0,  # 통신 단계별 대기 제한(초). 전체 작업의 총 제한은 아니다.
        )
        response.raise_for_status()  # 4xx/5xx를 성공 데이터로 읽지 않게 한다.
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 401:
            clear_private()
            st.session_state["notice"] = (
                "로그인에 실패했습니다. 입력 정보를 확인하세요." if path == "/auth/login" else
                "로그인 세션이 만료되었거나 유효하지 않습니다. 다시 로그인하세요."
            )
            st.rerun()
        elif status == 503:
            st.error("서버 또는 저장소가 일시적으로 응답하지 않습니다. 로그인 상태는 유지합니다.")
        elif status == 404:
            st.session_state.pop("messages", None)
            st.error("대화를 찾을 수 없습니다. 내 대화 목록을 다시 확인하세요.")
        else:
            st.error("요청에 실패했습니다. 상태 코드: " + str(status))
        st.stop()
    except httpx.RequestError:
        st.error("서버와 통신할 수 없습니다. 연결을 복구한 뒤 화면을 다시 실행하세요.")
        st.stop()  # 토큰·미확정 저장은 유지한다. 자동 재전송은 하지 않는다.
    return response.json()


def logout_and_clear():
    token = st.session_state.get("access_token", "")
    ended = False
    try:
        response = httpx.post(
            API_BASE_URL + "/auth/logout",
            headers={"Authorization": "Bearer " + token}, timeout=15.0,
        )
        ended = response.status_code in (200, 401)  # 이미 만료된 경우도 화면은 종료한다.
    except httpx.RequestError:
        pass  # 통신 실패여도 아래 로컬 상태 정리는 반드시 실행한다.
    clear_private()
    st.session_state["notice"] = (
        "로그아웃했습니다. 다시 로그인하세요." if ended else
        "화면의 로그인 정보는 지웠습니다. 서버 세션 종료는 확인하지 못했습니다."
    )
    st.rerun()


st.title("로그인 만료와 서버 장애를 구분하기")
st.caption("실제 인증과 DB 이력을 연결합니다. AI 답변 생성은 이 실습에 포함하지 않습니다.")
st.button("화면 다시 실행")  # 새 메시지 없이도 실행 흐름을 확인한다.
notice = st.session_state.pop("notice", None)
if notice:
    st.info(notice)

# [로그인 시작]
if not st.session_state["access_token"]:
    with st.form("login_form", clear_on_submit=True):  # 제출 뒤 입력칸을 기본값으로 비운다.
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")  # 화면에서 글자만 가린다. 암호화 수단은 아니다.
        submitted = st.form_submit_button("로그인")
    if submitted:
        if not email.strip() or not password:
            st.warning("이메일과 비밀번호를 입력하세요.")
        else:
            result = api("POST", "/auth/login", {"email": email.strip(), "password": password})
            clear_private()  # 새 인증 결과를 넣기 전에 이전 사용자 상태부터 지운다.
            st.session_state["access_token"] = result["access_token"]
            st.session_state["user"] = {"id": result["user_id"], "email": result["email"]}
            st.rerun()  # 로그인 폼을 숨기고 보호된 화면으로 넘어간다.
    st.stop()  # 미로그인 실행은 여기서 끝나므로 아래 개인 화면을 그리지 않는다.
# [로그인 끝]

if st.button("로그아웃"):
    logout_and_clear()

# [사용자 확인 시작]
# 로컬 토큰 존재는 화면 분기 조건일 뿐이다. 백엔드 /me로 실제 권한을 확인한다.
profile = api("GET", "/me")
st.session_state["user"] = {"id": profile["id"], "email": profile["email"]}
st.success("로그인 유지 중")
st.text("현재 계정: " + (profile["email"] or profile["id"]))
# [사용자 확인 끝]

# [만료 표시 시작]
st.caption(f"로그인 세션 남은 시간: {profile['ttl']}초 (조회 시점)")
# 자동 카운트다운이 아니다. 화면 다시 실행 버튼으로 최신 TTL을 조회한다.
# [만료 표시 끝]

# [목록 시작]
st.session_state["conversations"] = api("GET", "/conversations")
rooms = st.session_state["conversations"]
if not rooms:
    st.info("저장된 대화가 없습니다. BACKEND_GUIDE의 샘플 준비를 확인하세요.")
    st.stop()
# [목록 끝]

# [선택 시작]
# 제목은 중복될 수 있으므로 실제 options는 고유 ID 목록으로 만든다.
labels = {}
for room in rooms:
    labels[room["id"]] = room["title"] + " · " + room["id"][:8]
ids = list(labels)
# 위젯 생성 전에 유효성을 확인한다. 생성 뒤 같은 키를 대입하면 오류가 날 수 있다.
if st.session_state.get("selected_id") not in ids:
    st.session_state["selected_id"] = ids[0]


def room_label(room_id):
    return labels[room_id]  # 화면에 보일 문자열. 반환될 ID 자체는 바꾸지 않는다.


selected_id = st.selectbox(
    "대화 선택", ids,  # 선택 후보는 ID들이다. index 기본값은 0이다.
    format_func=room_label,  # 표시만 제목+ID 일부로 바꾼다. 기본은 값의 문자열 표시다.
    key="selected_id",  # 선택값과 session_state를 연결하는 이름이다.
)
# [선택 끝]

# [입력 시작]
# pending은 저장 결과가 확정되지 않은 메시지 한 개다. 화면 표시 이력과 분리한다.
pending = st.session_state.get("pending")
new_submission = False  # 기존 pending을 새 제출로 오인하지 않는다.
text = st.chat_input(
    "저장할 메시지를 입력하세요", disabled=pending is not None,  # 미확정 건 처리 전 새 제출을 막는다. 기본 False.
)
if text and pending is None:
    cleaned = text.strip()
    if not cleaned or len(cleaned) > 1000:
        st.warning("메시지는 공백을 제외하고 1~1000자로 입력하세요.")
    else:
        st.session_state["pending"] = {
            "conversation_id": selected_id, "request_id": str(uuid4()), "content": cleaned,
        }
        new_submission = True
pending = st.session_state.get("pending")
# [입력 끝]

# [재시도 시작]
retry = False
if pending:
    if pending["conversation_id"] != selected_id:
        st.warning("미확정 저장이 다른 대화에 있습니다. 원래 대화로 돌아가 확인하세요.")
    else:
        st.text("저장 확인 중인 메시지: " + pending["content"])
        retry = st.button("저장 확인/재시도")  # 같은 요청 ID로만 재전송한다.
# [재시도 끝]

# [저장 시작]
if pending and pending["conversation_id"] == selected_id and (new_submission or retry):
    saved = api("POST", f"/conversations/{selected_id}/messages", {
        "content": pending["content"], "request_id": pending["request_id"],
    })
    st.session_state["pending"] = None  # 성공 응답 확인 후에만 미확정 상태를 해제한다.
    st.session_state["notice"] = "저장을 확인했습니다. " + ("기존 저장 결과입니다." if saved["replayed"] else "새 기록입니다.")
    st.rerun()  # 입력창의 disabled를 풀고 새 DB 목록으로 화면을 다시 그린다.
# [저장 끝]

# [이력 조회 시작]
# 선택된 대화의 결과로 교체한다. 이전 대화 목록에 append/extend하지 않는다.
st.session_state["messages"] = []
st.session_state["messages"] = api("GET", f"/conversations/{selected_id}/messages")
# [이력 조회 끝]

# [말풍선 시작]
st.write("저장된 메시지 수:", len(st.session_state["messages"]))
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):  # role은 발화자 종류이고 로그인 계정 ID는 아니다.
        st.text(message["content"])
# [말풍선 끝]
