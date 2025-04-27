# main.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

import yfinance as yf

from fastapi.middleware.cors import CORSMiddleware

import requests
from bs4 import BeautifulSoup

from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import time

from llm import extract_keywords_llama, extract_keywords_gpt
import random

from sklearn.feature_extraction.text import TfidfVectorizer
from konlpy.tag import Okt  # 또는 Mecab

import os
from dotenv import load_dotenv

load_dotenv()

from requests.auth import HTTPBasicAuth

import json

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

app = FastAPI()

origins = [
    "https://stockus-fe.vercel.app",
    "http://localhost:9999"  # 정확한 프론트엔드 origin을 명시
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    # 구글 스프레드 시트에 저장
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
    ]

creds = ServiceAccountCredentials.from_json_keyfile_name("stock-project-456213-00f766c38980.json", scope)
client = gspread.authorize(creds)

# 미국 3대 지수 요약 (병렬 처리로 변경)
@app.get("/market_summary")
def get_market_summary():

    # 여러 종목의 데이터를 동시에 다운로드하는 함수
    def fetch_data(ticker):
        stock_df = yf.download(ticker)
        stock_df_tail = stock_df.tail(n=2)
        stock_df_tail_close = stock_df_tail["Close"]

        cur_close = round(stock_df_tail_close.iloc[1].item(), 2)
        prev_close = round(stock_df_tail_close.iloc[0].item(), 2)
        change_rate = round(((cur_close - prev_close) / prev_close * 100), 2)
        
        result = {
            "ticker": ticker,
            "prev_close": prev_close,
            "cur_close": cur_close,
            "change_rate": change_rate
        }

        return result

    us_3 = {"다우": "^DJI", "S&P500": "^GSPC", "나스닥": "^IXIC"}
    total_list = []
    
    with ThreadPoolExecutor() as executor:
        # 병렬로 여러 데이터를 가져오기
        results = executor.map(fetch_data, us_3.values())

    total_list.extend(results)
    
    return {"data": total_list}

# 미국 3대 지수 요약
'''
@app.get("/market_summary")
def get_market_summary():
    us_3 = { "다우": "^DJI", "S&P500": "^GSPC", "나스닥": "^IXIC"}
    total_list = []
    
    for key, value in us_3.items():
        # 각 지수의 전체 일자 데이터
        stock_df = yf.download(value)
        stock_df_tail = stock_df.tail(n=2) # 최근 2일 데이터 (등락률 계산 시 필요)
        stock_df_tail_close = stock_df_tail["Close"] # 종가만 추출

        # 등락률 계산: (오늘 종가 - 전일 종가 / 전일 종가) * 100
        cur_close = round(stock_df_tail_close.iloc[1][value], 2)
        prev_close = round(stock_df_tail_close.iloc[0][value], 2)

        change_rate = round(((cur_close - prev_close) / prev_close * 100), 2) # 셋째 자리에서 반올림
        print(change_rate)
        item = { 
                "ticker": value, 
                "prev_close": prev_close,
                "cur_close": cur_close,
                "change_rate": change_rate
                }
        total_list.append(item)
    
    return {"data": total_list}
'''

USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.5993.70 Safari/537.36",
    ]

headers = {"User-Agent": random.choice(USER_AGENTS)}

# [DC] 구글 스프레드 시트에 글 정보 저장
@app.get("/scrap_posts")
def scrap_posts():

    # 기존 스크래핑 데이터 열기
    sheet = client.open("stockus-posts").sheet1.get_all_records() # 객체 형태로 반환
    max_id = max(sheet, key=lambda x: x["id"]) # 현재까지 저장된 가장 큰 아이디 값
    
    while True:
        page_count = 1

        url = f"https://gall.dcinside.com/mgallery/board/lists/?id=stockus&page={page_count}" # 페이징으로 호출
        res = requests.get(url, headers=headers)

        # 1페이지에 있는 전체 글 번호, 제목, 링크 수집
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            contents_list = soup.find_all(
                lambda tag: (
                    tag.name == "tr"
                    and "us-post" in tag.get("class", [])
                    and tag.get("data-type") != "icon_notice" # 공지 설문 제외
                )
            )

            posts = []

            for i, row in enumerate(contents_list):
                print(i, row)

                post_id = row.select_one("td.gall_num").text.strip()
                if post_id == max_id:
                    continue

                title_tag = row.select_one("td.gall_tit a")
                date = row.select_one("td.gall_date").get("title")
                views = row.select_one("td.gall_count").text.strip()
                recommend = row.select_one("td.gall_recommend").text.strip()
                second_div = ""

                url = f"https://gall.dcinside.com/mgallery/board/view/?id=stockus&no={post_id}" # 개별 게시글 호출
                res = requests.get(url, headers=headers)

                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")

                    contents = soup.find("div", class_="write_div")
                    if contents == None:
                        continue
                    else:
                        divs = contents.find_all(["p", "span", "div"])
                        if len(divs) > 0:
                            second_div = " ".join(list(set([div.text for div in divs])))
                        time.sleep(1.5)

                post = {
                    "id": post_id,
                    "title": title_tag.text.strip(),
                    "date": date,
                    "views": views,
                    "recommend": recommend,
                    "contents": second_div
                }

                post_list = list(post.values())

                posts.append(post_list)
                # 마지막 게시글일 때
                if len(contents_list) - 1 == i:
                    page_count += 1 
        else:
            print(res)
            return

        sheet = client.open("stockus-posts").sheet1
        sheet.append_rows(posts)

        return

# [DC] 스크래핑 (멀티 스레딩)
@app.get("/scrap_posts_multi")
def scrap_posts_multi():
    start = time.time()

    # 기존 데이터 조회
    sheet = client.open("stockus-posts").worksheet("posts")
    row_count = len(sheet.get_all_values())
    print(row_count)

    # 기존 데이터 삭제
    if row_count > 1:
        sheet.batch_clear([f"A2:Z{row_count}"])

    # if len(sheet) > 0:
    #     max_id = max(sheet, key=lambda x: x["id"])["id"]
    # else:
    #     max_id = 0

    # 본문 스크래핑
    def fetch_post_data(post_id):
        url = f"https://gall.dcinside.com/mgallery/board/view/?id=stockus&no={post_id}"
        res = requests.get(url, headers=headers)
        time.sleep(random.uniform(0, 1)) # 0~1초 랜덤
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            contents = soup.find("div", class_="write_div")
            if contents:
                divs = contents.find_all(["p", "span", "div"])
                return " ".join(list(set([div.text for div in divs])))
        return ""
    
    # 페이지별 목록 스크래핑 
    def fetch_page_data(page_count):
        url = f"https://gall.dcinside.com/mgallery/board/lists/?id=stockus&page={page_count}&list_num=100" # 100개 단위로 소팅
        res = requests.get(url, headers=headers)
        # time.sleep(random.uniform(1, 2))  # 1~2초 랜덤 딜레이

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            contents_list = soup.find_all(
                lambda tag: (
                    tag.name == "tr"
                    and "us-post" in tag.get("class", [])
                    and tag.get("data-type") != "icon_notice"
                )
            )
            posts = []
            for row in contents_list:
                post_id = row.select_one("td.gall_num").text.strip()
                # if post_id == max_id:
                #     continue
                title_tag = row.select_one("td.gall_tit a")
                date = row.select_one("td.gall_date").get("title")
                views = row.select_one("td.gall_count").text.strip()
                recommend = row.select_one("td.gall_recommend").text.strip()
                contents = fetch_post_data(post_id)
                post = {
                    "id": post_id,
                    "title": title_tag.text.strip(),
                    "date": date,
                    "views": views,
                    "recommend": recommend,
                    "contents": contents.replace("- dc official App", "").strip(),
                }
                posts.append(post)
            return posts
        return []

    posts = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_page_data, page) for page in range(1, 6)]  # 1~3페이지까지 고정
        for future in as_completed(futures):
            posts.extend(future.result())

    sheet = client.open("stockus-posts").sheet1
    sheet.append_rows([list(post.values()) for post in posts])

    end = time.time()

    return {"status": "sucess", "posts_count": len(posts), "time": f"{end - start: 0.2f}초"}


import urllib.request

# llm 요약 조회 (파라미터로 커뮤니티 구분)
@app.get("/llm_summary")
def llm_summary(cm: str):

    if cm == 'dc': # dc
        sheet = client.open("stockus-posts").worksheet("summary")
        all_values = sheet.get_all_values()
        last_row = all_values[-1] if all_values else None; 
        #print(last_row)
        
        return { 
            "text": last_row[0],
            "time_stamp": last_row[1]
        }
    elif cm == 'rd': # reddit

        text = json.dumps(reddit_posts())
        result = extract_keywords_gpt(text, 'rd')
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

###### 레딧 ######

REDDIT_USER_NAME = os.getenv("REDDIT_USER_NAME")
REDDIT_CLINENT_ID = os.getenv("REDDIT_CLINENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")

# reddit 토큰 추가
@app.get("/reddit_token")
def get_token():

    data = {
    'grant_type': 'password',
    'username': REDDIT_USER_NAME,
    'password': REDDIT_PASSWORD
    }

    headers = {
    'User-Agent': f'python:stock-us:v1.0 (by /u/{REDDIT_USER_NAME})'
    }

    auth = HTTPBasicAuth(REDDIT_CLINENT_ID, REDDIT_CLIENT_SECRET)
    response_auth = requests.post(
    'https://www.reddit.com/api/v1/access_token',
    headers=headers,
    data=data,
    auth=auth
    )

    if response_auth.status_code == 200:
        print("Access token:", response_auth.json())
    else:
        print(response_auth)
        print(f"Error: {response_auth.status_code}")
        print(response_auth.text)
    return { "token": response_auth.json()['access_token']}

# reddit 최신 포스트 가져오기
@app.get("/reddit_posts")
def reddit_posts():
    token = get_token()["token"]

    time.sleep(1)

    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': f'python:stock-us:v1.0 (by /u/{REDDIT_USER_NAME})'
    }

    url = "https://oauth.reddit.com/r/wallstreetbets/new?limit=20" # wallstreetebets

    response = requests.get(url, headers=headers)
    data = json.loads(response.text)['data']['children']

    start_kst = datetime(2025, 4, 22, 20, 0)  # 2025-04-22 20:00 KST
    end_kst = datetime(2025, 4, 22, 21, 0)    # 2025-04-22 21:00 KST

    # UTC 변환
    start_utc = start_kst - timedelta(hours=9)
    end_utc = end_kst - timedelta(hours=9)

    start_ts = int(start_utc.replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(end_utc.replace(tzinfo=timezone.utc).timestamp())

    post_list = [
        {
            "title": post["data"]["title"],
            "selftext": post["data"]["selftext"],
            "created": post["data"]["created"],
            "utc_time": datetime.utcfromtimestamp(post["data"]["created"]).isoformat(),
            "kst_time": (datetime.utcfromtimestamp(post["data"]["created"]) + timedelta(hours=9)).isoformat()
        }
        for post in data
    ]

    #print('post_list', post_list)
    return post_list


# llm 요약 (dc)
@app.get("/summarize_by_llm_dc")
async def summarize_by_llm_dc():
    start = time.time()

    # 스프레드 시트에서 가져오기
    sheet = client.open("stockus-posts").worksheet("posts")
    all_data = sheet.get_all_records()

    full_text = ''

    for post in all_data:
        full_text += post["title"] + " " + post["contents"]

    print(len(full_text)) # 전체 글자수 확인
        
    result = extract_keywords_gpt(full_text, 'dc')
    #result = extract_keywords(" ".join(keywords_list))

    sheet = client.open("stockus-posts").worksheet("summary")

    KST = timezone(timedelta(hours=9))
    kst_now = datetime.now(KST)

    time_stamp = kst_now.strftime("%Y-%m-%d %H:%M:%S") # kst 기준
    sheet.append_rows([[result, time_stamp]])
    
    end = time.time()

    return {"data": result, "time": f"{end - start: 0.2f}초"}

# ping (sleep 방지용)
@app.get("/ping")
def ping():
    return {"msg": "pong!"}

@app.get("/")
def root():
    return {"status": "백엔드 살아있음!"}

# 테스트용
@app.get("/test")
def read_item():      

    try:
        response = urllib.request.urlopen('https://stockus-be.onrender.com/ping').headers['Date']
        print(response)  # ← 응답 본문 출력!
        return
        if date:
            print(f"서버 시간: {date}")
        else:
            print("Date 헤더가 없습니다.")
    except Exception as e:
        print(f"에러 발생: {e}")

    return

####

# 한글 전처리 함수
def tokenize_korean(text):
    okt = Okt()
    return [word for word, pos in okt.pos(text) if pos in ["Noun", "Verb", "Adjective"]]

# TF-IDF로 키워드 뽑기
@app.get("/extract_keywords")
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
    vectorizer = TfidfVectorizer(tokenizer=tokenize_korean) # 일단 불용어 제외

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

