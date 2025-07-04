from fastapi import APIRouter
from app.services.reddit import RedditService

router = APIRouter(prefix="/reddit", tags=["reddit"])

# reddit 토큰 추가
@router.get("/token")
def get_token():
    return RedditService.get_token()

# reddit 최신 포스트 가져오기
@router.get("/posts")
def get_reddit_posts():
    return RedditService.get_reddit_posts()


