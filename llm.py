import os
from dotenv import load_dotenv
import requests
from openai import OpenAI

import time
import random 

load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# 모델 토큰 제한
MAX_TOKENS = 8192
CHUNK_SIZE = 2000  # 보낼 때 여유를 두기 위한 크기

def extract_keywords_llama(text: str, count: int = 5) -> list[str]:
    # prompt = f'''다음은 한국인들의 미국 주식 커뮤니티의 글 내용들이야. 사람들이 미국 주식 현황에 대해서 어떻게 생각하고 있는지 2~3문장으로 요약해줘:\n{text}'''

    # prompt = f'''다음은 주식 커뮤니티에 올라온 글들이야.\n
    #             각 글에서 사람들이 어떤 종목에 관심을 보이고 있는지, 그리고 그 감정이 긍정/부정/혼합 중 어떤지 요약해서 알려줘:\n
    #             {text}\n
    #             요약 결과는 아래처럼 정리해줘:
    #             - 테슬라: 긍정 (상승 기대감)
    #             - 엔비디아: 부정 (과매수 우려)'''


    # prompt = f'''Here are some posts from a stock market community.\n
    #             Please summarize which stocks people are showing interest in and what kind of sentiment they are expressing — positive, negative, or mixed.\n
    #             Please organize the summary in the format below:
    #             {text}\n
    #             Tesla: Positive (Expecting price increase)\n
    #             Nvidia: Negative (Concerns of being overbought)'''
    
    prompt = f'''<|begin_of_text|><|start_header_id|>system<|end_header_id|> You are a financial data analyst summarizing posts from a Korean stock community. 
                For each post, extract:
                1. The company or stock mentioned (e.g. Tesla, Nvidia, Palantir)
                2. The sentiment expressed by the user: Positive, Negative, or Mixed
                3. The reason or context in 1 short sentence

                Format your answer like this:
                - Tesla: Positive (Expecting stock price to rise after strong sales report)
                - Nvidia: Mixed (Concern about US export restrictions, but long-term growth expected)

                Here is the posts: <|eot_id|><|start_header_id|>{text}<|end_header_id|>
                
                Answer: <|eot_id|><|start_header_id|>assistant<|end_header_id|>'''

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
    print('chunks', len(chunks))
    results = []
    for i, chunk in enumerate(chunks):
        if i == 3:
            break
        print('chunk 길이 확인', len(chunk))
        print('몇 번째 chunk:', i)
        data["messages"][0]["content"] = chunk
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()  # 요청 실패 시 예외 발생
        print(response.json())
        results.append(response.json()["choices"][0]["message"]["content"])
        time.sleep(random.uniform(2, 3))
    combined_text = " ".join(results)

    # response = requests.post(GROQ_API_URL, headers=headers, json=data)
    # response.raise_for_status()
    # result = response.json()

    # return result["choices"][0]["message"]["content"].strip().split("\n"

    # 최종 요약 요청
    # final_prompt = f'''지금까지 요약한 텍스트를 마지막으로 한번 더 요약하고 한국어로 번역해서 2~3문장으로 말해줘:\n{combined_text}'''
    # data["messages"][0]["content"] = final_prompt

    # 요약 요청
    # time.sleep(random.uniform(2, 3))

    # response = requests.post(GROQ_API_URL, headers=headers, json=data)
    # response.raise_for_status()  # 요청 실패 시 예외 발생
    # final_summary = response.json()["choices"][0]["message"]["content"]

    #return final_summary 
    return combined_text


def extract_keywords_gpt(text: str, count: int = 5) -> list[str]:
    client = OpenAI()

    OpenAI.api_key = os.getenv("OPENAI_API_KEY")

    prompt = f'''
                Here are some posts from a stock market community.

                Please summarize which **stocks** people are showing interest in and what kind of **sentiment** they are expressing — **positive, negative, or mixed**.

                - Don't limit the summary to only Tesla or Nvidia.  
                - If there are **other stocks mentioned**, please **include them** in the same format.
                - After the summary, please **translate it into Korean** in a **casual tone** like how Korean MZ generation talks — fun, trendy, and a bit playful like SNS captions or comment sections.

                Here are the posts:
                {text}

                Please organize the summary in the format below:

                - Tesla: Positive (가격 상승 기대중)
                - Nvidia: Negative (하락장 이어질까봐 불안함)
            '''

    print(len(text))
    return

    response = client.responses.create(
        model="gpt-4.1-nano",
        input=prompt
    )

    print(response.output_text)
    return