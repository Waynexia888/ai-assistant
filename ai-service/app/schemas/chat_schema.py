# app/schemas/chat_schema.py

from typing import Optional, Literal, List
from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str

class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(..., min_length=1)
    session_id: Optional[str] = Field("default", alias="sessionId")
    history: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    answer: str
    session_id: str = Field(..., alias="sessionId")
