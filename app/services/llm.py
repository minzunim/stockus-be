from oauth2client.service_account import ServiceAccountCredentials
import gspread
import time
from datetime import datetime, timezone, timedelta
import json

# 구글 스프레드 시트에 저장
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
    ]

creds = ServiceAccountCredentials.from_json_keyfile_name("stock-project-456213-00f766c38980.json", scope)
client = gspread.authorize(creds)

class LlmService:
    @staticmethod
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

    @staticmethod
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
