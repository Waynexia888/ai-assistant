import logging

from app.domain.tools.registry import ToolRegistry
from app.infrastructure.mcp.adapter import MCPToolAdapter
from app.infrastructure.mcp.config import MCPServerConfig
from app.infrastructure.mcp.stdio_client import StdioMCPClient


logger = logging.getLogger(__name__)


class MCPRuntime:
    def __init__(
        self,
        config: MCPServerConfig,
        client: StdioMCPClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or StdioMCPClient(config)
        self.adapter = MCPToolAdapter(client=self.client, config=config)
        self.last_error: str | None = None

    async def start(self, registry: ToolRegistry) -> bool:
        if not self.config.enabled:
            return False

        try:
            await self.client.connect()
            await self.adapter.register_tools(registry, replace=True)
        except BaseException as error:
            self.last_error = str(error)
            logger.warning(
                "Unable to start MCP server %s: %s",
                self.config.name,
                error,
            )
            await self.client.close()
            return False

        self.last_error = None
        return True

    async def close(self) -> None:
        await self.client.close()
