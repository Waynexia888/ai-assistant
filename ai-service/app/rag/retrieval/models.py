from pydantic import BaseModel, Field
from typing import Any


class RAGChunk(BaseModel):
    content: str
    score: float | None = None
    source: str | None = None
    title: str | None = None
    knowledge_base_id: str | None = None
    user_id: str | None = None
    chunk_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGSearchResult(BaseModel):
    query: str
    chunks: list[RAGChunk] = Field(default_factory=list)
    context: str = ""
    collection_name: str
