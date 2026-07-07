from typing import Any

from app.domain.models.tool_result import ToolResult
from app.infrastructure.mcp.browser_observation import BrowserObservationNormalizer


class BrowserActionNormalizer:
    def __init__(
        self,
        observation_normalizer: BrowserObservationNormalizer | None = None,
    ) -> None:
        self.observation_normalizer = (
            observation_normalizer or BrowserObservationNormalizer()
        )

    def normalize(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        raw_result: Any,
    ) -> ToolResult[dict[str, Any]]:
        observation_result = self.observation_normalizer.normalize(
            tool_name=tool_name,
            arguments=arguments,
            raw_result=raw_result,
        )
        observation_data = observation_result.data or {}
        return ToolResult(
            success=observation_result.success,
            message=observation_result.message,
            data={
                "type": "browser_action_result",
                "action": tool_name,
                "executed": observation_result.success,
                "content": observation_data.get("content"),
                "summary": observation_data.get("summary"),
                "observation": observation_data.get("observation", {}),
            },
        )

    def error(
        self,
        *,
        server: str,
        tool_name: str,
        arguments: dict[str, Any],
        error: Exception,
    ) -> ToolResult[dict[str, Any]]:
        observation_result = self.observation_normalizer.error(
            server=server,
            tool_name=tool_name,
            arguments=arguments,
            error=error,
        )
        observation_data = observation_result.data or {}
        return ToolResult(
            success=False,
            message=observation_result.message,
            data={
                "type": "browser_action_result",
                "action": tool_name,
                "executed": False,
                "content": observation_data.get("content"),
                "summary": observation_data.get("summary"),
                "observation": observation_data.get("observation", {}),
            },
        )
