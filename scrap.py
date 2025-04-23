import asyncio
from main import scrap_posts_multi, llm_summary
import time

def run_daily_scraper():
    print("스크래핑 시작!")
    asyncio.run(run_tasks_sequentially())

async def run_tasks_sequentially():
    start = time.time()
    scrap_posts_multi()
    await llm_summary('dc') # dc 크론 처리
    end = time.time()
    print(f"{end - start: 0.2f}초")

if __name__ == "__main__":
    run_daily_scraper()