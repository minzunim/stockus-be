import time
import requests
import random
import json

from oauth2client.service_account import ServiceAccountCredentials
import gspread

from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

from supabase_client import supabase

USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.5993.70 Safari/537.36",
    ]

headers = {"User-Agent": random.choice(USER_AGENTS)}

# 구글 스프레드 시트에 저장
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
    ]

creds = ServiceAccountCredentials.from_json_keyfile_name("stock-project-456213-00f766c38980.json", scope)
client = gspread.authorize(creds)

class ScrapService:
   
   # [DC] 구글 스프레드 시트에 글 정보 저장
   @staticmethod
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

   @staticmethod
   async def scrap_posts_multi():
       start = time.time()
       print('start', start)

       # 기존 데이터 조회
       '''
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
       '''

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
                      "post_id": post_id,
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

       '''
       sheet = client.open("stockus-posts").sheet1
       sheet.append_rows([list(post.values()) for post in posts])
       '''

       # posts 리스트를 supabase의 "post_dc" 테이블에 한 번에 batch insert 방식으로 저장

       if posts:
          data_to_insert = [
             {
                "post_id": post["post_id"],
                "title": post["title"],
                "date": post["date"],
                "views": post["views"],
                "recommend": post["recommend"],
                "contents": post["contents"],
             }
             for post in posts
          ]
          print(data_to_insert)

          # Supabase의 insert 메서드 사용 (더 안전하고 간단)
          response = supabase.table("post_dc").upsert(
                        data_to_insert, 
                        on_conflict='post_id',  # 중복 여부를 판단할 기준 컬럼
                        ignore_duplicates=True  # 중복 데이터는 무시하고 넘어가기
                    ).execute()
          
          # 응답 처리
          if response.data:
              print("데이터 가져오기 성공!")
              print(response.data)
          elif response.error:
              print(f"데이터 가져오기 오류: {response.error.message}")
          else:
              print("응답에 데이터나 오류가 없습니다.")

       end = time.time()

       return {"status": "sucess", "posts_count": len(posts), "time": f"{end - start: 0.2f}초"}
