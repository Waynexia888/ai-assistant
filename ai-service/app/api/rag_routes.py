from fastapi import APIRouter, HTTPException

from app.schemas.rag_schema import AddURLsRequest, AddURLsResponse
from app.rag.ingestion.add_urls import URLProcessor

router = APIRouter(prefix="/rag", tags=["RAG"])

url_processor = URLProcessor()

@router.post("/urls", response_model=AddURLsResponse)
async def add_urls(request: AddURLsRequest):
    result = await url_processor.add_urls(
       urls=request.urls,
       knowledge_base_id=request.knowledge_base_id,
       user_id="default",  # 第一版可以先 hard-code，后面接登录系统再改
       clean_before_chunking=request.clean_before_chunking
   )
   
    if result.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Failed to add URLs"),
        )

    return result
