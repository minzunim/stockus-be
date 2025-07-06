# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import urllib.request

from dotenv import load_dotenv

load_dotenv()

from requests.auth import HTTPBasicAuth

from app.routers import market, scrap, llm, reddit

app = FastAPI()

origins = [
    "https://stockus-fe.vercel.app",
    "http://localhost:9999"  # 정확한 프론트엔드 origin을 명시
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# router
app.include_router(market.router)
app.include_router(reddit.router)
app.include_router(llm.router)
app.include_router(scrap.router)

# ping (sleep 방지용)
@app.get("/ping")
def ping():
    return {"msg": "pong!"}

@app.get("/")
def root():
    return {"status": "백엔드 살아있음!"}

# 테스트용
@app.get("/test")
def read_item():      

    try:
        response = urllib.request.urlopen('https://stockus-be.onrender.com/ping').headers['Date']
        print(response)  # ← 응답 본문 출력!
        return
        if date:
            print(f"서버 시간: {date}")
        else:
            print("Date 헤더가 없습니다.")
    except Exception as e:
        print(f"에러 발생: {e}")

    return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)