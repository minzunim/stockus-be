import os
from dotenv import load_dotenv
import requests

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def extract_keywords(text: str, count: int = 5) -> list[str]:
    prompt = f'''다음 텍스트는 미국 주식 관련 커뮤니티에 올라온 글의 제목과 본문이야.\n
                텍스트를 분석해서 지금 사람들이 미국 주식과 관련해서 무엇을 관심있게 얘기하는지 알고 싶어.\n 
                주요 키워드 {count}개만 뽑아줘:\n\n{text}'''

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

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()

    return result["choices"][0]["message"]["content"].strip().split("\n")

'''{
keywords: [
"Here are 5 major keywords related to stock market and trading that I extracted from the text:",
"",
"1. **NASDAQ** (나스닥) - mentioned multiple times in the text, indicating that the author is interested in the performance of the NASDAQ stock market.",
"2. **-Trump** (트럼프) - mentioned several times, suggesting that the author is interested in the impact of Trump's policies and actions on the stock market.",
"3. **Long/Short** (롱/숏) - mentioned frequently, indicating that the author is engaged in trading activities and is concerned with long-term investments vs. short-term gains/losses.",
"4. **Tariffs** (관세) - mentioned several times, indicating that the author is interested in the impact of trade tariffs on the stock market and economy.",
"5. **AAPL** (애플) - mentioned once, indicating that the author is interested in the performance of Apple Inc.'s stock.",
"",
"These keywords suggest that the author is an active trader or investor interested in the US stock market, particularly in the tech sector, and is paying close attention to geopolitical events and their impact on the market."
]
}
'''

# 프롬프트가 중요하겠다. 단순히 키워드 뽑아내는 것만이 중요할까...?
# 그리고 8000자 이 정도도 그런데 그 이상을 음..