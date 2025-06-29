from fastapi import APIRouter
from app.services.market import MarketService

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/summary")
def get_market_summary():
    return MarketService.get_market_summary()