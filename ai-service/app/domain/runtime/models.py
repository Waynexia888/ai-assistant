from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.llm.messages import LLMMessage, LLMToolCall
from app.domain.models.tool_trace import ToolExecutionTrace


RuntimeEventType = Literal[
    "llm_call_started",
    "llm_call_completed",
    "tool_call_started",
    "tool_call_completed",
    "tool_call_failed",
    "approval_required",
    "runtime_iteration_completed",
    "runtime_completed",
    "runtime_failed",
]


class ToolRuntimeEvent(BaseModel):
    type: RuntimeEventType
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class ToolTraceItem(BaseModel):
    tool_call: LLMToolCall
    success: bool
    result: Any | None = None
    error: str | None = None
    execution_trace: ToolExecutionTrace | None = None


class ToolCallingRuntimeResult(BaseModel):
    final_message: LLMMessage | None = None
    final_text: str | None = None
    messages: list[LLMMessage] = Field(default_factory=list)
    tool_traces: list[ToolTraceItem] = Field(default_factory=list)
    events: list[ToolRuntimeEvent] = Field(default_factory=list)
    iterations: int = 0
    stopped_reason: str | None = None
