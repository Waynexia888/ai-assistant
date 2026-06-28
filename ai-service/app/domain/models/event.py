from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone
from typing import Literal, Any, Optional, Union

from .plan import Plan, Step
from .tool_result import ToolResult



class BaseEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanEvent(BaseEvent):
    type: Literal["plan"] = "plan"
    status: Literal["created", "updated", "completed"]
    plan: Plan

class StepEvent(BaseEvent):
    type: Literal["step"] = "step"
    status: Literal["started", "completed", "failed"]
    step: Step
    
class ToolEvent(BaseEvent):
    type: Literal["tool"] = "tool"
    status: Literal["calling", "called", "failed"]
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Optional[ToolResult[Any]] = None
    trace: dict[str, Any] | None = None


class RuntimeEvent(BaseEvent):
    type: Literal["runtime"] = "runtime"
    event_type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)

class MessageEvent(BaseEvent):
    type: Literal["message"] = "message"
    role: Literal["user", "assistant"] = "assistant"
    message: str


class ErrorEvent(BaseEvent):
    type: Literal["error"] = "error"
    error: str


class DoneEvent(BaseEvent):
    type: Literal["done"] = "done"
    


Event = Union[
    PlanEvent,
    StepEvent,
    ToolEvent,
    RuntimeEvent,
    MessageEvent,
    ErrorEvent,
    DoneEvent,
]
