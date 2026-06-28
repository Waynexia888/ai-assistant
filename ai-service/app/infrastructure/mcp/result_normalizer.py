from typing import Any

from pydantic import BaseModel

from app.domain.models.tool_result import ToolResult


class MCPResultNormalizer:
    """Convert MCP SDK or JSON-shaped results into the runtime ToolResult."""

    def normalize(self, raw_result: Any) -> ToolResult[Any]:
        if isinstance(raw_result, ToolResult):
            return raw_result

        payload = self._to_plain_value(raw_result)
        if not isinstance(payload, dict):
            return ToolResult(success=True, data=payload)

        is_error = bool(payload.get("isError", payload.get("is_error", False)))
        content = payload.get("content")
        structured_content = payload.get(
            "structuredContent",
            payload.get("structured_content"),
        )
        message = self._message_from_content(content) if is_error else None

        data: Any
        if structured_content is not None:
            data = structured_content
        elif content is not None:
            data = {"content": self._to_plain_value(content)}
        else:
            data = payload

        return ToolResult(
            success=not is_error,
            message=message,
            data=data,
        )

    def error(
        self,
        *,
        server: str,
        tool: str,
        error: Exception,
    ) -> ToolResult[dict[str, Any]]:
        return ToolResult(
            success=False,
            message=str(error),
            data={
                "type": "mcp_tool_error",
                "server": server,
                "tool": tool,
                "message": str(error),
                "retryable": False,
            },
        )

    def _to_plain_value(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [self._to_plain_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_plain_value(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): self._to_plain_value(item)
                for key, item in value.items()
            }
        return value

    def _message_from_content(self, content: Any) -> str:
        plain_content = self._to_plain_value(content)
        if isinstance(plain_content, str):
            return plain_content
        if isinstance(plain_content, list):
            messages = [
                item.get("text")
                for item in plain_content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ]
            if messages:
                return "\n".join(messages)
        return "MCP tool returned an error."
