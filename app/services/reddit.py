from datetime import datetime, timedelta, timezone
import json
import os
import time
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth

load_dotenv()

REDDIT_USER_NAME = os.getenv("REDDIT_USER_NAME")
REDDIT_CLINENT_ID = os.getenv("REDDIT_CLINENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")

class RedditService:
    # reddit access_token 발급
    @staticmethod
    def get_token():

        start = time.time()
        data = {
        'grant_type': 'password',
        'username': REDDIT_USER_NAME,
        'password': REDDIT_PASSWORD
        }

        headers = {
        'User-Agent': f'python:stock-us:v1.0 (by /u/{REDDIT_USER_NAME})'
        }

        # base64로 인코딩해서 헤더에 전달
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
        
        end = time.time()

        return { "token": response_auth.json()['access_token']}

    # reddit 최신 포스트 가져오기
    @staticmethod
    def get_reddit_posts():
        token = RedditService.get_token()["token"]

        time.sleep(1)

        start = time.time()
        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': f'python:stock-us:v1.0 (by /u/{REDDIT_USER_NAME})'
        }

        url = "https://oauth.reddit.com/r/wallstreetbets/new?limit=20" # wallstreetebets

        response = requests.get(url, headers=headers)
        data = json.loads(response.text)['data']['children']

        end = time.time()
        # print(f"소요시간1: {end - start}")

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
        
        end2 = time.time()
        # print(f"소요시간2: {end2 - end}")

        #print('post_list', post_list)
        return post_list