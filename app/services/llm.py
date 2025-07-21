from oauth2client.service_account import ServiceAccountCredentials
import gspread
import time
from datetime import datetime, timezone, timedelta
import json
import requests
import random 
import os
from dotenv import load_dotenv
import asyncio

from openai import OpenAI

from app.services.reddit import RedditService
from konlpy.tag import Okt  # 또는 Mecab
from sklearn.feature_extraction.text import TfidfVectorizer

from openai import AsyncOpenAI
from supabase_client import supabase

load_dotenv()

# 구글 스프레드 시트에 저장
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
    ]

creds = ServiceAccountCredentials.from_json_keyfile_name("stock-project-456213-00f766c38980.json", scope)
client = gspread.authorize(creds)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# 모델 토큰 제한
MAX_TOKENS = 8192
CHUNK_SIZE = 2000  # 보낼 때 여유를 두기 위한 크기

class LlmService:
    @staticmethod
    async def extract_keywords_gpt(text: str, cm: str) -> list[str]:
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) # 비동기로 요청

        #OpenAI.api_key = os.getenv("OPENAI_API_KEY")

        prompt = f'''
                    #명령문
                    너는 주식 애널리스트야.
                    다음 텍스트는 미국 주식에 대해 얘기하는 { '한국' if cm == 'dc' else '전세계인의' } 주식 커뮤니티 게시글들을 모은 거야.
                    이 텍스트를 보고 유저들이 현재 관심 있는 주식 종목명(ticker) 10개와 어떤 평가를 하는지 20자 내로 요약해줘.

                    #출력 형식
                    [{{
                        "ticker": "[해당 ticker]"
                        "summary": "[해당 ticker에 대한 유저들의 평가]"
                        "Rating": "[buy, hold, sell 중 하나]"
                    }}, ...]
                '''
        
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )

        # print(response.output_text)
        return response.choices[0].message.content

    """비동기 버전의 GPT 키워드 추출"""
    @staticmethod
    async def extract_keywords_gpt_async(text: str, cm: str) -> str:
        
        # 동기 함수를 비동기로 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, LlmService.extract_keywords_gpt, text, cm)
        return result

    # DC 스크래핑 저장된 게시글 전체 조회 -> llm으로 요약 후 시트에 저장
    @staticmethod
    async def summarize_by_llm_dc():
        start = time.time()

        # 스프레드 시트에서 가져오기
        '''
        sheet = client.open("stockus-posts").worksheet("posts")
        all_data = sheet.get_all_records()
        '''
        # 오늘 날짜 계산 (KST 기준)
        KST = timezone(timedelta(hours=9))
        today = datetime.now(KST).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=KST)

        # 오늘 날짜 데이터만 조회
        today_posts = supabase.table("post_dc").select("*").gte("date", today_start.isoformat()).execute()
        print(today_posts)

        full_text = ''

        for post in today_posts.data:
            full_text += post["title"] + " " + post["contents"]

        print(len(full_text)) # 전체 글자수 확인
            
        result = await LlmService.extract_keywords_gpt(full_text, 'dc')
        #result = extract_keywords(" ".join(keywords_list))

        #sheet = client.open("stockus-posts").worksheet("summary")
        print(result)

        # KST = timezone(timedelta(hours=9))
        # kst_now = datetime.now(KST)

        time_stamp = today.strftime("%Y-%m-%d %H:%M:%S") # kst 기준
        #sheet.append_rows([[result, time_stamp]])
        
        end = time.time()

        return {"data": result, "time": f"{end - start: 0.2f}초"}

    # llm 요약 글 조회
    # DC: 시트에 저장된 요약 조회 / Reddit: 시트 저장 x -> Reddit API 호출 후 바로 llm 요약
    @staticmethod
    async def llm_summary(cm: str):
        if cm == 'dc': # dc
            sheet = client.open("stockus-posts").worksheet("summary")
            all_values = sheet.get_all_values()
            last_row = all_values[-1] if all_values else None; 
        #print(last_row)
            
            if last_row:
                return { 
                    "text": last_row[0],
                    "time_stamp": last_row[1]
                }
            else:
                return { 
                    "text": "데이터가 없습니다.",
                    "time_stamp": "" 
                    }

        elif cm == 'rd': # reddit

            text = json.dumps(RedditService.get_reddit_posts())

            #task1 = asyncio.create_task(LlmService.extract_keywords_gpt(text, 'rd'))
            
            result = await LlmService.extract_keywords_gpt(text, 'rd')
            KST = timezone(timedelta(hours=9))
            kst_now = datetime.now(KST)

            return {
                "text": result,
                "time_stamp": kst_now.strftime("%Y-%m-%d %H:%M:%S") # kst 기준
            }
        else: 
            return {
                "text": "잘못된 요청입니다.",
                "time_stamp": ""
            }

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
    
    # 한글 전처리 함수
    def tokenize_korean(text):
        okt = Okt()
        return [word for word, pos in okt.pos(text) if pos in ["Noun", "Verb", "Adjective"]]

    # TF-IDF로 키워드 뽑기
    def tfIdf():    

        # 스프레드 시트에서 가져오기
        sheet = client.open("stockus-posts").sheet1
        
        title_data = sheet.col_values(2)[1:]
        print(title_data)
        contents_data = sheet.col_values(6)[1:]
        print(contents_data)

        concat_list = [val for pair in zip(title_data, contents_data) for val in pair if val != '' or val != '- dc official App']   
        print(concat_list)
        full_text = " ".join(concat_list).replace("- dc official App","") # 전체 텍스트 합침

        custom_stopwords = [
        # 추임새, 반응
        'ㅋㅋ', 'ㅎㅎ', 'ㅠㅠ', 'ㅜㅜ', 'ㄷㄷ', '헐', '음', '와', '아', '오', '요', '네', '응', '진짜', '그냥',

        # 불필요한 맥락 단어
        '주식', '종목', '시장', '뉴스', '이슈', '글', '댓글', '영상', '기사', '정보', '분석',
        '투자', '매수', '매도', '매매', '가격', '오늘', '내일', '이번', '다음', '최근', '지금', '아직',

        # 표현 + 조사
        '근데', '그런데', '뭔가', '뭐지', '뭐야', '때문에', '그리고', '그래서', '하지만',
        '진짜', '너무', '많이', '좀', '좀더', '더', '되게', '많이', '많음', '많다',
        
        # 기타 filler words
        '사람', '개미', '외인', '기관', '나', '너', '걔', '우리', '이거', '저거', '그거',
        
        # 자주 나오는 약어/무의미 단어
        'ㅇㅇ', 'ㄴㄴ', 'ㅅㅂ', 'ㅈㄴ', 'ㄹㅇ', 'ㅁㅊ', 'ㅇㅋ', 'ㄱㄱ', 'ㄴㅇㅅ', 'ㅂㅂ',
        
        # 숫자/단위
        '억', '만원', '원', '퍼센트', '프로', '달러',

        # 종목명에 자주 붙는 단어
        '지주', '홀딩스', '테크', '바이오', '랩', '산업', '전자', '인터내셔널', '그룹'
        ]

        # TF-IDF 벡터라이저
        vectorizer = TfidfVectorizer(tokenizer=LlmService.tokenize_korean) # 일단 불용어 제외

        # 분석
        tfidf_matrix = vectorizer.fit_transform(concat_list)
        terms = vectorizer.get_feature_names_out()

        # 상위 키워드 추출
        scores = tfidf_matrix.toarray().sum(axis=0)
        #print(scores)
        keywords = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
        #print(keywords)

        keywords_list = []

        # 출력 (상위 10개)
        for word, score in keywords:
            # print(f"{word}: {round(score, 4)}")
            # print(word)
            keywords_list.append(word)
            print('keywords_list', keywords_list)

        return keywords_list