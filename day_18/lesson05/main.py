"""5차시: 제목이 같은 대화도 ID로 구분해 선택하기"""
# 환경변수는 .env 로드 후 조회한다. 실제 값은 화면이나 로그에 출력하지 않는다.
import os
import httpx
import streamlit as st
from dotenv import load_dotenv

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


def clear_private():
    # 현재 차시에서 사용하는 개인 상태만 지운다. 전체 세션을 무조건 clear하지 않는다.
    for key in ('access_token', 'user', 'conversations', 'selected_id', 'messages'):
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
            st.error("로그인 정보가 없거나 유효하지 않습니다. 화면을 다시 실행해 로그인하세요.")
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


st.title("제목이 같은 대화도 ID로 구분해 선택하기")
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
