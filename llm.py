import os
from dotenv import load_dotenv
import requests

import time
import random 

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# 모델 토큰 제한
MAX_TOKENS = 8192
CHUNK_SIZE = 2000  # 보낼 때 여유를 두기 위한 크기

def extract_keywords(text: str, count: int = 5) -> list[str]:
    prompt = f'''다음 텍스트를 분석해서 미국 주식 현황을 2~3문장으로 요약해줘:\n{text}'''

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    results = []
    for chunk in chunks:
        data["messages"][0]["content"] = chunk
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()  # 요청 실패 시 예외 발생
        print(response.json())
        results.append(response.json()["choices"][0]["message"]["content"])
        time.sleep(random.uniform(1, 2))
    combined_text = " ".join(results)

    # response = requests.post(GROQ_API_URL, headers=headers, json=data)
    # response.raise_for_status()
    # result = response.json()

    # return result["choices"][0]["message"]["content"].strip().split("\n"

    # 최종 요약 요청
    final_prompt = f'''지금까지 요약한 텍스트를 마지막으로 한번 더 요약하고 한국어로 번역해서 2~3문장으로 말해줘:\n{combined_text}'''
    data["messages"][0]["content"] = final_prompt

    # 요약 요청
    time.sleep(random.uniform(2, 3))

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()  # 요청 실패 시 예외 발생
    final_summary = response.json()["choices"][0]["message"]["content"]

    return final_summary
