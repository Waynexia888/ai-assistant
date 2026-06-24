from fastapi import APIRouter, HTTPException

from app.schemas.rag_schema import (
    AddFilesRequest,
    AddFilesResponse,
    AddURLsRequest,
    AddURLsResponse,
)
from app.rag.ingestion.add_urls import URLProcessor
from app.rag.ingestion.service import FileIngestionService

router = APIRouter(prefix="/rag", tags=["RAG"])

_url_processor: URLProcessor | None = None
_file_ingestion_service: FileIngestionService | None = None


def get_url_processor() -> URLProcessor:
    global _url_processor

    if _url_processor is None:
        _url_processor = URLProcessor()

    return _url_processor


def get_file_ingestion_service() -> FileIngestionService:
    global _file_ingestion_service

    if _file_ingestion_service is None:
        _file_ingestion_service = FileIngestionService()

    return _file_ingestion_service


@router.post("/urls", response_model=AddURLsResponse)
async def add_urls(request: AddURLsRequest):
    processor = get_url_processor()
    result = await processor.add_urls(
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


@router.post("/files", response_model=AddFilesResponse)
async def add_files(request: AddFilesRequest):
    service = get_file_ingestion_service()
    result = await service.add_files(
        paths=request.paths,
        knowledge_base_id=request.knowledge_base_id,
        user_id="default",  # 第一版可以先 hard-code，后面接登录系统再改
        clean_before_chunking=request.clean_before_chunking,
        batch_size=request.batch_size,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=500,
            detail=result.get("message", "Failed to add files"),
        )

    return result
