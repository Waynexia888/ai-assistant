from typing import Any, Literal
from pydantic import BaseModel, Field


StepResultType = Literal[
    "text",
    "tool_result",
    "rag_search_result",
    "llm_tool_calling_result",
    "browser_observation_result",
    "error",
]


class StepResult(BaseModel):
    type: StepResultType = "text"
    content: str | None = None
    data: dict[str, Any] | list[Any] | str | int | float | bool | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
