"""FastAPI 응답을 화면에 표시하는 Streamlit 앱. 모델은 로드하지 않는다."""
import os
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv


def read_backend_url():
    load_dotenv(override=False, interpolate=False)  # 프로세스 환경변수 우선, 문자열 치환 안 함.
    value = os.getenv("BACKEND_URL")
    if value is None or not value.strip():
        raise ValueError("BACKEND_URL 설정이 필요합니다.")
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("BACKEND_URL에는 http:// 또는 https:// 주소를 설정하세요.")
    return value


def request_answer(backend_url, prompt):
    with requests.post(
        f"{backend_url}/chat",  # Streamlit 서버가 FastAPI를 HTTP로 호출한다.
        json={"prompt": prompt},  # Python 딕셔너리를 JSON 요청 본문으로 보낸다.
        timeout=(5, 180),  # 연결 5초, 응답 읽기 대기 180초. 총 실행 시간 제한과 다르다.
    ) as response:
        response.raise_for_status()  # HTTP 4xx/5xx는 답변으로 취급하지 않는다.
        data = response.json()  # 완성된 JSON 응답을 Python 값으로 변환한다.
    if not isinstance(data, dict) or not isinstance(data.get("answer"), str) or not data["answer"].strip():
        raise ValueError("answer 문자열이 없는 응답입니다.")
    return data["answer"]



def main():
    st.title("백엔드가 답하는 학습 도우미")
    st.caption("FastAPI · 로컬 CPU · 완성된 답변")
    try:
        backend_url = read_backend_url()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()  # FastAPI와는 별개로 이 화면의 실행만 중단한다.

    prompt = st.chat_input("짧은 질문을 입력하세요")
    if prompt is None:
        return
    prompt = prompt.strip()
    if not prompt or len(prompt) > 500:
        st.warning("공백을 제외한 1~500자의 질문을 입력하세요.")
        return

    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        try:
            with st.spinner("백엔드가 답변을 생성하고 있습니다..."):
                answer = request_answer(backend_url, prompt)
            st.write(answer)
        except requests.HTTPError as exc:
            st.error(f"백엔드 요청 실패: HTTP {exc.response.status_code}. 실행 버전과 입력을 확인하세요.")
        except requests.RequestException:
            st.error("백엔드 연결이 끊겼거나 응답을 기다리다 실패했습니다. 서버 상태를 확인하세요.")
        except (ValueError, RuntimeError):
            st.error("답변 생성이 완료되지 않았습니다. 현재 표시된 내용은 완성된 답변이 아닙니다.")



if __name__ == "__main__":
    main()