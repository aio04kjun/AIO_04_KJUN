import argparse
import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from huggingface_hub import snapshot_download
import streamlit as st

def read_setting():
    load_dotenv()
    settings = {}
    for key in ('HF_MODEL_ID','MODEL_DIR'):
        value = os.getenv(key)
        settings[key] = value
    model_dir = Path(settings['MODEL_DIR']).expanduser()  # 상대경로
    # 모델경로는 main.py가 있는 폴더를 기준으로
    if not model_dir.is_absolute():
        model_dir = Path(__file__).resolve().parent / model_dir
    return settings['HF_MODEL_ID'], model_dir.resolve()

def download_model(model_id, model_dir):
    # 공개 모델의 필요한 파일만 다운로드 ONNX등 다른형식은 받지 않는다
    snapshot_download(
        repo_id=model_id,
        local_dir=str(model_dir),
        allow_patterns=[  # 모델구조 생성설정 토크나이저 가중치 이용조건만 받는다
            "config.json", "generation_config.json", "tokenizer*.json",
            "vocab.json", "merges.txt", "*.safetensors", "README.md", "LICENSE*",
        ]
    )
    print('다운로드 완료')

# Streamlit이 같은 인자로 다시 호출하면 모델을 메모리에서 재사용한다.
# 모델 파일 교체 후에는 서버를 재시작해야 새 모델이 로드된다.
@st.cache_resource
def load_local_model(model_dir):
    # 존재하지 않는 경로가 온라인 저장소 ID로 오해되지 않게 먼저 검사한다.
    if not Path(model_dir).is_dir():
        raise ValueError("모델 폴더가 없습니다. 먼저 python main.py download를 실행하세요.")
    # 다운로드만 할 때는 무거운 PyTorch와 Transformers를 불러오지 않는다.
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(4)  # CPU 연산에 사용할 스레드 수. PC별 최적값은 다르다.
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,  # 파일이 없으면 실패하며, 온라인 다운로드로 대체하지 않는다.
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        dtype=torch.float32,  # CPU 호환성을 우선한 32비트 실수. 양자화가 아니다.
        local_files_only=True,  # 가중치도 로컬 파일에서만 읽는다.
    )
    model.to("cpu")  # GPU 자동 선택 없이 CPU를 명시한다.
    model.eval()  # 학습용 dropout 등을 평가 모드로 바꾼다. 학습을 수행하지 않는다.
    # 캐시된 모델을 공유하므로 한 프로세스 안에서 생성 호출을 순서대로 실행한다.
    return tokenizer, model, Lock()


def generate_answer(tokenizer, model, lock, prompt):
    import torch

    # 이번 입력 한 개만 보낸다. 이전 질문·답변을 자동으로 기억하지 않는다.
    messages = [
        {"role": "system", "content": "한국어로 짧고 쉬운 문장으로 답하세요."},
        {"role": "user", "content": prompt},
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,  # 모델의 대화 형식을 적용한 뒤 토큰 번호로 바꾼다.
        add_generation_prompt=True,  # 이제 assistant의 답변이 시작될 위치를 표시한다.
        return_dict=True,  # input_ids와 attention_mask를 담은 딕셔너리로 받는다.
        return_tensors="pt",  # PyTorch가 계산할 텐서 형식으로 받는다.
    )
    input_length = inputs["input_ids"].shape[1]
    if input_length > 512:
        raise ValueError("입력이 너무 깁니다. 짧은 질문으로 줄여 주세요.")
    # 락은 공유 모델 호출을 직렬화하고, inference_mode는 역전파 기록을 끈다.
    with lock, torch.inference_mode():
        outputs = model.generate(
            **inputs,  # 입력 토큰과 attention_mask를 이름 있는 인자로 전달한다.
            max_new_tokens=96,  # 새 답변 토큰의 상한. 글자 수와 다르다.
            do_sample=False,  # 무작위 샘플링 대신 점수가 높은 토큰을 고른다.
            pad_token_id=tokenizer.eos_token_id,  # 이 단일 입력에서 패딩용 ID를 명시한다.
        )
    # generate의 결과에는 입력도 포함된다. 새로 생성된 부분만 잘라서 읽는다.
    answer = tokenizer.decode(
        outputs[0][input_length:],
        skip_special_tokens=True,  # 종료 표시 같은 제어 토큰을 화면에서 숨긴다.
    ).strip()
    if not answer:
        raise ValueError("빈 답변이 생성되었습니다. 다른 짧은 질문으로 다시 시도하세요.")
    return answer

def show_app(model_dir):
    st.title('로컬모델')
    st.caption("cpu 로컬모델 한번의 질문과 답변")
    prompt = st.chat_input('짧은 질문을 입력하세요')
    if prompt is None:
        st.info("모델을 다운로드 중입니다...")
        return
    # 문자 제한 토큰 제한은 토크나이져별로 확인
    if len(prompt) > 500:
        st.warning("질문을 500자 이내로 줄여주세요")
    with st.chat_message('user'):
        st.write(prompt)
    with st.chat_message('assistant'):
        with st.spinner('로컬모델이 답변을 생성하고 있습니다.'):
            tokenizer,model,lock =  load_local_model(str(model_dir))
            answer = generate_answer(tokenizer,model,lock,prompt)
        st.write(answer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'command', nargs="?", default='app', choices=['download','app']
    )
    args = parser.parse_args()
    try:
        model_id, model_dir = read_setting()        
    except ValueError as err:
        parser.error(str(err))
    else:
        if args.command == 'download':
            download_model(model_id=model_id,model_dir=model_dir)
        else:
            show_app(model_dir)
if __name__ =="__main__":
    main()