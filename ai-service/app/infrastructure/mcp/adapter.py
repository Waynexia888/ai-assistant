from typing import Any

from app.domain.models.tool import (
    ToolDefinition,
    ToolParameter,
    ToolParameterType,
    ToolSource,
)
from app.domain.models.tool_result import ToolResult
from app.domain.tools.base import BaseTool
from app.domain.tools.registry import ToolRegistry
from app.infrastructure.mcp.client import MCPClient
from app.infrastructure.mcp.browser_observation import BrowserObservationNormalizer
from app.infrastructure.mcp.config import MCPServerConfig
from app.infrastructure.mcp.result_normalizer import MCPResultNormalizer


SUPPORTED_PARAMETER_TYPES: set[str] = {
    "string",
    "number",
    "integer",
    "boolean",
    "object",
    "array",
}


class MCPToolProxy(BaseTool):
    def __init__(
        self,
        definition: ToolDefinition,
        adapter: "MCPToolAdapter",
    ) -> None:
        self.name = definition.name
        self.description = definition.description
        self._definition = definition
        self._adapter = adapter

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult[Any]:
        return await self._adapter.invoke(self.name, arguments)


class MCPToolAdapter:
    def __init__(
        self,
        client: MCPClient,
        config: MCPServerConfig,
        normalizer: MCPResultNormalizer | None = None,
        browser_normalizer: BrowserObservationNormalizer | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.normalizer = normalizer or MCPResultNormalizer()
        self.browser_normalizer = browser_normalizer or BrowserObservationNormalizer()
        self._definitions: dict[str, ToolDefinition] = {}
        self._mcp_names: dict[str, str] = {}

    async def discover_tools(self) -> list[ToolDefinition]:
        raw_tools = await self.client.list_tools()
        definitions: dict[str, ToolDefinition] = {}
        mcp_names: dict[str, str] = {}

        for raw_tool in raw_tools:
            raw_name = raw_tool.get("name")
            if (
                self.config.allowed_tools is not None
                and raw_name not in self.config.allowed_tools
            ):
                continue
            definition, mcp_name = self._map_tool(raw_tool)
            if definition.name in definitions:
                raise ValueError(
                    f"Duplicate MCP tool mapping for internal name: {definition.name}"
                )
            definitions[definition.name] = definition
            mcp_names[definition.name] = mcp_name

        self._definitions = definitions
        self._mcp_names = mcp_names
        return list(definitions.values())

    async def register_tools(
        self,
        registry: ToolRegistry,
        *,
        replace: bool = False,
    ) -> list[ToolDefinition]:
        definitions = await self.discover_tools()
        for definition in definitions:
            registry.register(
                MCPToolProxy(definition=definition, adapter=self),
                replace=replace,
            )
        return definitions

    async def invoke(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult[Any]:
        if tool_name not in self._mcp_names:
            await self.discover_tools()

        mcp_tool_name = self._mcp_names.get(tool_name)
        if mcp_tool_name is None:
            return ToolResult(
                success=False,
                message=f"MCP tool not found: {tool_name}",
                data={
                    "type": "mcp_tool_not_found",
                    "server": self.config.name,
                    "tool": tool_name,
                },
            )

        try:
            raw_result = await self.client.call_tool(mcp_tool_name, arguments)
        except Exception as error:
            if tool_name.startswith("browser."):
                return self.browser_normalizer.error(
                    server=self.config.name,
                    tool_name=tool_name,
                    arguments=arguments,
                    error=error,
                )
            return self.normalizer.error(
                server=self.config.name,
                tool=tool_name,
                error=error,
            )

        if tool_name.startswith("browser."):
            return self.browser_normalizer.normalize(
                tool_name=tool_name,
                arguments=arguments,
                raw_result=raw_result,
            )
        return self.normalizer.normalize(raw_result)

    def _map_tool(
        self,
        raw_tool: dict[str, Any],
    ) -> tuple[ToolDefinition, str]:
        mcp_name = raw_tool.get("name")
        if not isinstance(mcp_name, str) or not mcp_name:
            raise ValueError("MCP tool is missing a valid name")

        internal_name = self.config.internal_tool_name(mcp_name)
        input_schema = raw_tool.get("inputSchema", raw_tool.get("input_schema", {}))
        if not isinstance(input_schema, dict):
            input_schema = {}

        required_names = {
            name
            for name in input_schema.get("required", [])
            if isinstance(name, str)
        }
        properties = input_schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}

        parameters = [
            self._map_parameter(name, schema, name in required_names)
            for name, schema in properties.items()
            if isinstance(name, str)
        ]

        definition = ToolDefinition(
            name=internal_name,
            description=str(raw_tool.get("description") or ""),
            parameters=parameters,
            risk_level=self.config.risk_level_for(mcp_name),
            source=ToolSource.MCP,
            metadata={
                "mcp_server": self.config.name,
                "mcp_tool_name": mcp_name,
                "mcp_input_schema": input_schema,
            },
        )
        return definition, mcp_name

    def _map_parameter(
        self,
        name: str,
        raw_schema: Any,
        required: bool,
    ) -> ToolParameter:
        schema = raw_schema if isinstance(raw_schema, dict) else {}
        raw_type = schema.get("type", "object")
        parameter_type: ToolParameterType = (
            raw_type if raw_type in SUPPORTED_PARAMETER_TYPES else "object"
        )
        enum = schema.get("enum")

        return ToolParameter(
            name=name,
            type=parameter_type,
            description=str(schema.get("description") or ""),
            required=required,
            enum=(
                [str(value) for value in enum]
                if isinstance(enum, list)
                else None
            ),
            default=schema.get("default"),
            metadata={"json_schema": schema},
        )
