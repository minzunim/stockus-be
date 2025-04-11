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

from llm import extract_keywords


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

# 구글 스프레드 시트에 글 정보 저장
@app.get("/post_scrap")
def post_scrap():

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    url = f"https://gall.dcinside.com/mgallery/board/lists/?id=stockus&page=1" # 페이징으로 호출
    res = requests.get(url, headers=headers)

    # 1페이지에 있는 전체 글 번호, 제목, 링크 수집
    if res.status_code == 200:
        # request 결과 파싱해서 soup에 저장
        soup = BeautifulSoup(res.text, "html.parser")
        
        posts = []

        for row in soup.find_all("tr", class_="ub-content")[9:]:

            post_id = row.select_one("td.gall_num").text.strip()

            title_tag = row.select_one("td.gall_tit a")
            date = row.select_one("td.gall_date").get("title")
            views = row.select_one("td.gall_count").text.strip()
            recommend = row.select_one("td.gall_recommend").text.strip()
            second_div = ""

            url = f"https://gall.dcinside.com/mgallery/board/view/?id=stockus&no={post_id}" # 페이징으로 호출
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

            # if not title_tag:
            #     continue  # 제목 없는 건 스킵

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
    else:
        print(res)
        return

    sheet = client.open("미주마갤 스크래핑").sheet1
    sheet.append_rows(posts)

    return

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

# 키워드 추출
@app.get("/extract_keywords")
async def get_keywords():
    # 스프레드 시트에서 가져오기
    sheet = client.open("미주마갤 스크래핑").sheet1
    
    title_data = sheet.col_values(2)[1:]
    contents_data = sheet.col_values(6)[1:]

    concat_list = [val for pair in zip(title_data, contents_data) for val in pair if val != '' or val != '- dc official App']
    full_text = " ".join(concat_list).replace("- dc official App","")
    
    #print(len(full_text.replace(" ", "")))

    result = extract_keywords(full_text)
    return {"keywords": result}