"""1차시: 메시지를 만드는 함수 한 곳을 바꿔 연속 대화를 완성한다."""
import os

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI


SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "한국어로 두 문장 안에서 답하세요. "
        "대화에 나온 정보를 사용하고, 알려주지 않은 개인 정보는 모른다고 말하세요."
    ),
}


def build_messages(history, question):
    # 시작 코드: 이번 질문만 보낸다. 이 함수를 수정해 지난 대화도 함께 보낸다.
    current = [{"role": "user", "content": question}]
    return [SYSTEM_MESSAGE] + current


def main():
    # 현재 실습 폴더의 설정을 읽는다. 이미 설정된 환경변수는 유지한다.
    load_dotenv(".env", override=False, interpolate=False)
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    api_key = os.getenv("LLM_API_KEY", "")
    for name, value in {
        "LLM_BASE_URL": base_url, "LLM_MODEL": model, "LLM_API_KEY": api_key,
    }.items():
        if not value.strip():
            print(f".env의 {name} 항목을 입력하세요.")
            return
    if not base_url.startswith(("http://", "https://")):
        print(".env의 LLM_BASE_URL 주소 형식을 확인하세요.")
        return

    # 이 프로그램을 실행하는 동안 사용할 대화 목록이다.
    history = []
    print("대화를 시작합니다. 끝내려면 종료를 입력하세요.")

    with OpenAI(
        base_url=base_url, api_key=api_key,
        timeout=120.0,  # 로컬 모델의 응답을 기다리는 통신 제한(초).
        max_retries=0,  # 오류가 나면 안내하고 다음 입력을 기다린다.
    ) as client:
        while True:
            try:
                question = input("나: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n대화를 마칩니다.")
                break
            if question == "종료":
                break
            if not question:
                print("질문을 입력하세요.")
                continue

            messages = build_messages(history, question)
            # 저장한 개수가 아니라, 실제로 보낼 이전 메시지 개수를 확인한다.
            print("함께 보내는 이전 메시지:", len(messages) - 2, "개")
            try:
                response = client.chat.completions.create(model=model, messages=messages)
            except (APIConnectionError, APIStatusError):
                print("API 요청에 실패했습니다. 서버 실행과 .env 설정을 확인하세요.")
                continue

            answer = response.choices[0].message.content if response.choices else None
            if not answer or not answer.strip():
                print("답변을 받지 못했습니다. 질문을 다시 입력하세요.")
                continue

            print("AI:", answer.strip())
            # 질문과 답변을 한 쌍으로 남긴다. 실패한 요청은 목록에 넣지 않는다.
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer.strip()})


if __name__ == "__main__":
    main()
