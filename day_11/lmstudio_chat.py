"""VS Code 터미널용 LM Studio 채팅. Python 표준 라이브러리만 사용합니다."""

import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, ProxyHandler


def api_request(base_url, endpoint, api_key, payload=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        base_url + endpoint,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    # 로컬 요청이 시스템 프록시로 전달되는 것을 방지합니다.
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)


def list_models(base_url, api_key):
    with api_request(base_url, "/models", api_key, timeout=5) as response:
        data = json.load(response)
    return [item["id"] for item in data.get("data", [])
            if item.get("id") and "embed" not in item["id"].lower()]


def stream_reply(base_url, api_key, model, messages, first_token=None):
    payload = {"model": model, "messages": messages, "stream": True,
               "temperature": 0.7, "max_tokens": 2048}
    parts = []
    with api_request(base_url, "/chat/completions", api_key, payload) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            event = json.loads(data)
            if "error" in event:
                raise ValueError(f"모델 응답 오류: {event['error']}")
            choices = event.get("choices", [])
            if not choices:
                continue
            content = choices[0].get("delta", {}).get("content")
            if content:
                if first_token is not None:
                    first_token.set()
                print(content, end="", flush=True)
                parts.append(content)
    if not parts:
        raise ValueError("텍스트 답변이 없습니다. 채팅용 모델을 선택해 주세요.")
    return "".join(parts)


def reply_with_status(base_url, api_key, model, messages):
    """별도 스레드로 요청하여 느린 로컬 추론 중에도 진행 상태를 표시합니다."""
    finished = threading.Event()
    first_token = threading.Event()
    result = {}

    def generate():
        try:
            result["reply"] = stream_reply(base_url, api_key, model, messages, first_token)
        except Exception as error:
            result["error"] = error
        finally:
            finished.set()

    print("AI 응답 요청 중입니다. 모델 로드/추론 속도에 따라 시간이 걸릴 수 있습니다.", flush=True)
    print("AI > ", end="", flush=True)
    worker = threading.Thread(target=generate, daemon=True)
    worker.start()
    started = time.monotonic()
    while not finished.wait(15):
        if not first_token.is_set():
            print(f"\n[첫 답변 대기 중 · {int(time.monotonic() - started)}초 경과]", flush=True)
    if "error" in result:
        raise result["error"]
    return result["reply"]


def describe_error(error):
    if isinstance(error, HTTPError):
        detail = error.read().decode("utf-8", errors="replace")[:1500]
        return f"HTTP {error.code}: {detail}\n모델 로드 상태와 API 토큰 설정을 확인하세요."
    if isinstance(error, (URLError, TimeoutError)):
        return (f"LM Studio 연결 실패: {error}\n"
                "LM Studio의 Developer에서 서버를 시작하고 포트 번호를 확인하세요.\n"
                "예: python day_11/lmstudio_chat.py --url http://localhost:1234/v1")
    return str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("LM_STUDIO_URL", "http://localhost:1235/v1"))
    parser.add_argument("--model", help="사용할 정확한 모델 ID")
    parser.add_argument("--check", action="store_true", help="연결 및 모델 목록만 확인")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        parser.error("--url에는 http://localhost:1235/v1 형식의 주소를 입력하세요.")
    if not parsed.path.rstrip("/"):
        base_url += "/v1"
    api_key = os.getenv("LM_STUDIO_API_KEY", "")
    try:
        models = list_models(base_url, api_key)
        if not models:
            print("채팅 모델이 없습니다. LM Studio에서 채팅용 모델을 다운로드하고 로드하세요.")
            return 1
        print(f"\nLM Studio 연결: {base_url}")
        for index, model_id in enumerate(models, 1):
            print(f"  {index}. {model_id}")
        if args.check:
            return 0
        if args.model:
            if args.model not in models:
                print("지정한 모델이 목록에 없습니다. 위 목록의 정확한 ID를 사용하세요.")
                return 1
            model = args.model
        elif len(models) == 1:
            model = models[0]
        else:
            while True:
                choice = input("모델 번호 [1]: ").strip() or "1"
                if choice.isdecimal() and 1 <= int(choice) <= len(models):
                    model = models[int(choice) - 1]
                    break
                print("목록에 있는 번호를 입력하세요.")
        system = {"role": "system", "content": "당신은 친절하고 정확한 AI 도우미입니다. 기본적으로 한국어로 답하세요."}
        messages = [system]
        print(f"\n사용 모델: {model}\n/exit 종료 · /clear 대화 초기화 · /save 대화 저장")
        print("'나 >'는 질문 입력 대기입니다. 여기에 질문을 쓰고 Enter를 누르세요.")
        print("예: 파이썬의 리스트를 설명해줘. Ctrl+C로도 종료할 수 있습니다.\n")
        while True:
            prompt = input("나 > ").strip()
            if not prompt:
                continue
            if prompt.lower() == "/exit":
                break
            if prompt.lower() == "/clear":
                messages = [system]
                print("대화를 초기화했습니다.\n")
                continue
            if prompt.lower() == "/save":
                folder = Path(__file__).resolve().parent / "chat_logs"
                try:
                    folder.mkdir(exist_ok=True)
                    path = folder / f"chat_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
                    path.write_text(json.dumps({"model": model, "messages": messages},
                                               ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"저장했습니다: {path}\n")
                except OSError as error:
                    print(f"저장 실패: {error}\n")
                continue
            pending = messages + [{"role": "user", "content": prompt}]
            try:
                reply = reply_with_status(base_url, api_key, model, pending)
            except (URLError, TimeoutError, OSError, ValueError) as error:
                print(f"\n{describe_error(error)}\n질문은 대화 기록에 추가되지 않았습니다.\n")
                continue
            messages = pending + [{"role": "assistant", "content": reply}]
            print("\n")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\n채팅을 종료합니다.")
        return 0
    except (URLError, TimeoutError, OSError, ValueError) as error:
        print(describe_error(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
