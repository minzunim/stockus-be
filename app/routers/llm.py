from fastapi import APIRouter, Query
from app.services.llm import LlmService

router = APIRouter(prefix="/llm", tags=["llm"])

# llm 요약 (dc)
@router.get("/summarize_by_llm_dc")
async def summarize_by_llm_dc():
   return LlmService.summarize_by_llm_dc()

# llm 요약 조회 (파라미터로 커뮤니티 구분)
@router.get("/summary")
async def llm_summary(cm):
   return LlmService.llm_summary(cm)