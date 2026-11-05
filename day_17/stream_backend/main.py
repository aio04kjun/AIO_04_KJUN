"""FastAPI 응답을 화면에 표시하는 Streamlit 앱. 모델은 로드하지 않는다."""
import os
from urllib.parse import urlparse
import json
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


def request_stream(backend_url, prompt):
    with requests.post(
        f"{backend_url}/chat/stream",
        json={"prompt": prompt},
        stream=True,  # 본문 전체가 완성될 때까지 한꺼번에 읽지 않는다.
        timeout=(5, 180),  # 연결 대기와 데이터 읽기 대기를 따로 제한한다.
    ) as response:
        response.raise_for_status()  # 422/503 등은 스트림 읽기 전에 구분한다.
        response.encoding = "utf-8"  # 한국어 바이트를 올바른 문자열로 복원한다.
        done = False
        has_text = False
        # 줄 경계까지 모아 JSON을 해석한다. 작은 chunk_size로 초기 버퍼 지연을 줄인다.
        for line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if not line:
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("잘못된 스트림 형식입니다.")
            if event.get("type") == "delta" and isinstance(event.get("text"), str):
                text = event["text"]
                has_text = has_text or bool(text.strip())
                yield text  # write_stream이 받는 것은 JSON 객체가 아니라 텍스트다.
            elif event.get("type") == "done":
                done = True
                break
            else:  # error 이벤트 또는 알 수 없는 형식은 정상 답변으로 저장하지 않는다.
                raise RuntimeError("스트림이 정상 완료되지 않았습니다.")
        if not done or not has_text:
            raise RuntimeError("완료 신호 또는 답변 내용이 없습니다.")
    # with를 빠져나오면 HTTP 연결 자원을 닫는다.



def main():
    st.title("생성 중인 답변을 읽는 학습 도우미")
    st.caption("FastAPI · 로컬 CPU · 실제 생성 스트리밍")
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
            st.write_stream(request_stream(backend_url, prompt))
        except requests.HTTPError as exc:
            st.error(f"백엔드 요청 실패: HTTP {exc.response.status_code}. 실행 버전과 입력을 확인하세요.")
        except requests.RequestException:
            st.error("백엔드 연결이 끊겼거나 응답을 기다리다 실패했습니다. 서버 상태를 확인하세요.")
        except (ValueError, RuntimeError):
            st.error("답변 생성이 완료되지 않았습니다. 현재 표시된 내용은 완성된 답변이 아닙니다.")



if __name__ == "__main__":
    main()