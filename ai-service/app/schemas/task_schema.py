
from pydantic import BaseModel, Field
from typing import Any
from app.domain.models.plan import Plan



class TaskRequest(BaseModel):
    message: str = Field(..., min_length=1)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    summary: str | None 
    plan: Plan | None
    events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None

