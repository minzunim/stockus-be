import asyncio
from app.services.scrap import ScrapService
from app.services.llm import LlmService
import time

from supabase_client import supabase # 이렇게 import 하면 돼!

def supabase_test():
    print('supabase test')
    response = supabase.table("post_dc").select("*").execute()
    print(response)

def run_daily_scraper():
    print("스크래핑 시작!")
    asyncio.run(run_tasks_sequentially())

async def run_tasks_sequentially():
    start = time.time()
    #await ScrapService.scrap_posts_multi()
    await LlmService.summarize_by_llm_dc() # dc 크론 처리
    end = time.time()
    print(f"{end - start: 0.2f}초")

if __name__ == "__main__":
    run_daily_scraper()
    #supabase_test()
    #LlmService.summarize_by_llm_dc()