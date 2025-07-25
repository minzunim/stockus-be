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
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
print('url', url)

key: str = os.environ.get("SUPABASE_KEY")
print('key', key)

supabase: Client = create_client(url, key)