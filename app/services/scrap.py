class ScrapService:
   @staticmethod
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
