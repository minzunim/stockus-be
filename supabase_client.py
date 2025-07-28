'''
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

url: str = os.getenv("SUPABASE_URL")
print('url', url)
key: str = os.getenv("SUPABASE_KEY")
print('key', key)

supabase: Client = create_client(url, key)
'''

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 파일 로드
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
print('url', url)

key: str = os.environ.get("SUPABASE_KEY")
print('key', key)

# 환경 변수가 없으면 에러 발생
if not url or not key:
    raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경 변수를 설정해주세요.")

supabase: Client = create_client(url, key)