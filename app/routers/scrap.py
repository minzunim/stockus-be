from fastapi import APIRouter
from app.services.scrap import ScrapService

router = APIRouter(prefix="/scrap", tags=["scrap"])

# [DC] 스크래핑 (멀티 스레딩)
@router.get("/scrap_posts_multi")
def scrap_posts_multi():
    return ScrapService.scrap_posts_multi()
