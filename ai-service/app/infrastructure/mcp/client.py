from typing import Any, Protocol


class MCPClient(Protocol):
    """Transport-independent boundary for an MCP server connection."""

    async def list_tools(self) -> list[dict[str, Any]]:
        ...

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        ...
