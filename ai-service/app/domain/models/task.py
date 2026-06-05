

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

from .plan import Plan
from .event import Event


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    status: TaskStatus = TaskStatus.PENDING
    plan: Optional[Plan] = None
    events: List[Event] = Field(default_factory=list)
    summary: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
