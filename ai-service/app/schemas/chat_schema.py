# app/schemas/chat_schema.py

from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    feeling: Optional[dict[str, Any]] = None