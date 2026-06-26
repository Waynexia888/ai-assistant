from typing import Any, Literal, Protocol

from pydantic import BaseModel

from app.domain.llm.messages import LLMMessage
from app.domain.models.tool import ToolDefinition


ToolChoice = Literal["auto", "none"]


class LLMResponse(BaseModel):
    message: LLMMessage
    raw: dict[str, Any] | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> LLMResponse:
        ...
