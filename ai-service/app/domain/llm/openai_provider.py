import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.domain.llm.messages import LLMMessage, LLMToolCall
from app.domain.llm.provider import LLMResponse, ToolChoice
from app.domain.llm.tool_schema import to_openai_tool_schema
from app.domain.models.tool import ToolDefinition


class OpenAIChatProvider:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url or settings.OPENAI_API_BASE or None,
        )
        self.model = model or settings.BASE_MODEL

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        tool_choice: ToolChoice | None = "auto",
    ) -> LLMResponse:
        openai_tools = [
            to_openai_tool_schema(tool)
            for tool in tools or []
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                self._to_openai_message(message)
                for message in messages
            ],
            tools=openai_tools or None,
            tool_choice=tool_choice if openai_tools else None,
        )

        choice = response.choices[0]

        return LLMResponse(
            message=self._from_openai_message(choice.message),
            raw=response.model_dump(mode="json"),
            finish_reason=choice.finish_reason,
            usage=response.usage.model_dump(mode="json") if response.usage else None,
        )

    def _to_openai_message(self, message: LLMMessage) -> dict[str, Any]:
        if message.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "name": message.name,
                "content": message.content or "",
            }

        payload: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }

        if message.tool_calls:
            payload["tool_calls"] = [
                self._to_openai_tool_call(tool_call)
                for tool_call in message.tool_calls
            ]

        return payload

    def _to_openai_tool_call(self, tool_call: LLMToolCall) -> dict[str, Any]:
        return {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.name,
                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
            },
        }

    def _from_openai_message(self, message: Any) -> LLMMessage:
        tool_calls = [
            LLMToolCall(
                id=tool_call.id,
                name=tool_call.function.name,
                arguments=self._parse_tool_arguments(tool_call.function.arguments),
            )
            for tool_call in message.tool_calls or []
        ]

        return LLMMessage(
            role="assistant",
            content=message.content,
            tool_calls=tool_calls,
        )

    def _parse_tool_arguments(self, raw_arguments: str | None) -> dict[str, Any]:
        if not raw_arguments:
            return {}

        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {"_raw": raw_arguments}

        if isinstance(parsed, dict):
            return parsed

        return {"value": parsed}
