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

# 모델 설정
class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
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

@app.get("/market_summary")
def get_market_summary():
    # 미국 3대 지수
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

USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.5993.70 Safari/537.36",
    ]

headers = {"User-Agent": random.choice(USER_AGENTS)}

# 구글 스프레드 시트에 글 정보 저장
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

# 멀티 스레딩 테스트용  
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


# llm 요약
@app.get("/summarize_by_llm")
async def summarize_by_llm():
    start = time.time()

    # 기존 데이터 조회
    sheet = client.open("stockus-posts").worksheet("summary")
    row_count = len(sheet.get_all_values())
    print(row_count)

    # 기존 데이터 삭제
    if row_count > 1:
        sheet.batch_clear([f"A1:Z{row_count}"])

    # 스프레드 시트에서 가져오기
    sheet = client.open("stockus-posts").sheet1
    all_data = sheet.get_all_records()

    # 정렬
    #important_posts = sorted(all_data, key=lambda x: int(x["views"]), reverse=True)[:20]
    important_posts = sorted(all_data, key=lambda x: int(x["views"]), reverse=True)
    print(important_posts)

    full_text = ''

    for post in important_posts:
        full_text += post["title"] + " " + post["contents"]

    # title_data = sheet.col_values(2)[1:]
    # contents_data = sheet.col_values(6)[1:]

    # concat_list = [val for pair in zip(title_data, contents_data) for val in pair if val != '' or val != '- dc official App']   
    # full_text = " ".join(concat_list).replace("- dc official App","")

    # keywords_list = tfIdf() # tfIdf 결과로 추출하기
    # print('keywords_list', keywords_list)
    # print(full_text)
    print(len(full_text)) # 전체 글자수 확인
    result = extract_keywords_gpt(full_text)
    #result = extract_keywords(" ".join(keywords_list))

    sheet = client.open("stockus-posts").worksheet("summary")

    time_stamp = time.strftime('%Y-%m-%d %H:%M:%S') # 년.월.일 - 시간
    print('시간', time_stamp)
    sheet.append_rows([[result, time_stamp]])
    
    end = time.time()

    return {"data": result, "time": f"{end - start: 0.2f}초"}

# llm 요약 조회
@app.get("/llm_summary")
async def llm_summary():
    
    sheet = client.open("stockus-posts").worksheet("summary")
    all_values = sheet.get_all_values()
    last_row = all_values[-1] if all_values else None; 
    print(last_row)

    return { 
        "text": last_row[0],
        "time_stamp": last_row[1]
    }

# 테스트용
@app.get("/test")
def read_item():      
    html = '''<div class="write_div" style="overflow:hidden;width:900px;" data-tracking="feb09862036defa1cb39229b3c4b4107c46f6805a6653be982e20534f83c45">
							<p>ㅇㅇ?</p>							
							</div>'''
    soup = BeautifulSoup(html, "html.parser")
    contents = soup.find("div", class_="write_div")
    list = contents.find_all(["p", "div"])
    print(list)

    return

# ping
@app.get("/ping")
def ping():
    return {"msg": "pong!"}