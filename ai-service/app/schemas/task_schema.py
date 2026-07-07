from typing import Any

from pydantic import BaseModel, Field

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
    pending_approval_id: str | None = None


class TaskEventListResponse(BaseModel):
    task_id: str
    status: str
    final_result: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: int = 0
    done: bool = False
