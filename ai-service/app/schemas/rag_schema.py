from typing import List, Optional, Literal

from pydantic import BaseModel, Field

class AddURLsRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1)
    knowledge_base_id: Optional[str] = None
    clean_before_chunking: bool = True

class AddURLsResponse(BaseModel):
    status: Literal["success", "warning", "error"]  # 表示 status 只能是这三种字符串之一。
    message: str
    url_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    collection_name: Optional[str] = None


class AddFilesRequest(BaseModel):
    paths: List[str] = Field(..., min_length=1)
    knowledge_base_id: Optional[str] = None
    clean_before_chunking: bool = True
    batch_size: int = Field(default=1000, ge=1, le=10000)


class AddFilesResponse(BaseModel):
    status: Literal["success", "warning", "error"]
    message: str
    file_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    collection_name: Optional[str] = None
