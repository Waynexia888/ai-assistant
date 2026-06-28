from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.infrastructure.mcp.config import MCPServerConfig


class StdioMCPClient:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @property
    def connected(self) -> bool:
        return self._session is not None

    async def connect(self) -> None:
        if self.connected:
            return
        if not self.config.command:
            raise ValueError(
                f"MCP server command is not configured: {self.config.name}"
            )

        stack = AsyncExitStack()
        try:
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=self.config.command,
                        args=self.config.args,
                        env=self.config.env or None,
                    )
                )
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
        except BaseException:
            await stack.aclose()
            raise

        self._exit_stack = stack
        self._session = session

    async def close(self) -> None:
        stack = self._exit_stack
        self._session = None
        self._exit_stack = None
        if stack is not None:
            await stack.aclose()

    async def list_tools(self) -> list[dict[str, Any]]:
        session = self._require_session()
        result = await session.list_tools()
        return [
            tool.model_dump(mode="json", by_alias=True)
            for tool in result.tools
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        session = self._require_session()
        result = await session.call_tool(name, arguments=arguments)
        return result.model_dump(mode="json", by_alias=True)

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError(
                f"MCP server is not connected: {self.config.name}"
            )
        return self._session
