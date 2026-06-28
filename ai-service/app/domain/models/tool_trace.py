from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolExecutionTrace(BaseModel):
    trace_id: str
    source: Literal["builtin", "mcp"]
    mcp_server: str | None = None
    internal_tool_name: str
    mcp_tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    success: bool
    result_type: str
    error: str | None = None
