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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    #OpenAI.api_key = os.getenv("OPENAI_API_KEY")

    prompt = f'''
                다음 텍스트는 미국 주식에 대해 얘기하는 한국 주식 커뮤니티 게시글들을 모은 거야
                이 대화 내용을 보고 사람들이 현재 어떤 주식에 관심을 갖고 그 주식들에 어떤 감정을 갖고 있는지 표현해줘 (긍정, 부정, 중립)
                형식은 다음과 같이 출력해줘.

                📌 [주식 종목명] (감정): 한 줄 요약1. 한 줄 요약2.
                📌 [주식 종목명] (감정): 한 줄 요약1. 한 줄 요약2.
                ✨ 전반적인 분위기 요약 (2-3문장 정도로 간결하게, 친근한 말투로)
            '''

    print(len(text))

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ]
    )

    # print(response.output_text)
    return response.choices[0].message.content