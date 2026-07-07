from typing import Any

from app.domain.models.tool import (
    ToolDefinition,
    ToolParameter,
    ToolParameterType,
    ToolSource,
)
from app.domain.models.browser import BrowserElement
from app.domain.models.tool_result import ToolResult
from app.domain.tools.base import BaseTool
from app.domain.tools.registry import ToolRegistry
from app.infrastructure.mcp.client import MCPClient
from app.infrastructure.mcp.browser_observation import BrowserObservationNormalizer
from app.infrastructure.mcp.browser_action import BrowserActionNormalizer
from app.infrastructure.mcp.browser_action_target import BrowserActionTargetResolver
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

BROWSER_ACTION_TOOL_NAMES = {"browser.click", "browser.type"}


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
        browser_action_normalizer: BrowserActionNormalizer | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.normalizer = normalizer or MCPResultNormalizer()
        self.browser_normalizer = browser_normalizer or BrowserObservationNormalizer()
        self.browser_action_normalizer = (
            browser_action_normalizer
            or BrowserActionNormalizer(self.browser_normalizer)
        )
        self.target_resolver = BrowserActionTargetResolver()
        self._definitions: dict[str, ToolDefinition] = {}
        self._mcp_names: dict[str, str] = {}
        self._last_browser_observation: dict[str, Any] = {}
        self._last_browser_elements: list[BrowserElement] = []

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

        if tool_name == "browser.type" and arguments.get("submit") is True:
            return ToolResult(
                success=False,
                message="browser.type cannot submit forms in Phase 8.",
                data={
                    "type": "tool_denied",
                    "tool_name": tool_name,
                    "reason": "Form submission is not enabled.",
                },
            )

        call_arguments = arguments
        if tool_name in BROWSER_ACTION_TOOL_NAMES:
            prepared = await self._prepare_browser_action_arguments(
                tool_name=tool_name,
                arguments=arguments,
            )
            if isinstance(prepared, ToolResult):
                return prepared
            call_arguments = prepared

        try:
            raw_result = await self.client.call_tool(mcp_tool_name, call_arguments)
        except Exception as error:
            if tool_name in BROWSER_ACTION_TOOL_NAMES:
                return self.browser_action_normalizer.error(
                    server=self.config.name,
                    tool_name=tool_name,
                    arguments=call_arguments,
                    error=error,
                )
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

        if tool_name in BROWSER_ACTION_TOOL_NAMES:
            result = self.browser_action_normalizer.normalize(
                tool_name=tool_name,
                arguments=call_arguments,
                raw_result=raw_result,
            )
            self._remember_browser_observation(result.data)
            return result
        if tool_name.startswith("browser."):
            result = self.browser_normalizer.normalize(
                tool_name=tool_name,
                arguments=call_arguments,
                raw_result=raw_result,
            )
            self._remember_browser_observation(result.data)
            return result
        return self.normalizer.normalize(raw_result)

    async def _prepare_browser_action_arguments(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | ToolResult[Any]:
        if self._has_explicit_ref(arguments):
            explicit = dict(arguments)
            explicit.setdefault("element", explicit.get("ref"))
            explicit.setdefault("target", explicit.get("element") or explicit.get("ref"))
            return self._shape_browser_action_arguments_for_mcp(tool_name, explicit)

        match = self.target_resolver.resolve(
            arguments=arguments,
            elements=self._last_browser_elements,
            include_text_argument=tool_name != "browser.type",
        )
        if match is None:
            await self._refresh_browser_observation_cache()
            match = self.target_resolver.resolve(
                arguments=arguments,
                elements=self._last_browser_elements,
                include_text_argument=tool_name != "browser.type",
            )

        if match is None or match.ref is None:
            return self._target_not_found_result(tool_name, arguments)

        resolved = self.target_resolver.resolved_arguments(
            arguments=arguments,
            match=match,
        )
        return self._shape_browser_action_arguments_for_mcp(tool_name, resolved)

    async def _refresh_browser_observation_cache(self) -> None:
        observe_mcp_name = self._mcp_names.get("browser.observe")
        if observe_mcp_name is None:
            return

        try:
            raw_result = await self.client.call_tool(observe_mcp_name, {})
        except Exception:
            return

        result = self.browser_normalizer.normalize(
            tool_name="browser.observe",
            arguments={},
            raw_result=raw_result,
        )
        self._remember_browser_observation(result.data)

    def _remember_browser_observation(self, data: Any) -> None:
        if not isinstance(data, dict):
            return

        observation = data.get("observation")
        if not isinstance(observation, dict):
            return

        self._last_browser_observation = observation

        elements = observation.get("elements")
        if not isinstance(elements, list):
            self._last_browser_elements = []
            return

        parsed = [
            BrowserElement.model_validate(element)
            for element in elements
            if isinstance(element, dict)
        ]
        self._last_browser_elements = parsed

    def _target_not_found_result(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult[Any]:
        observation = self._target_not_found_observation_context()
        reason = self._target_not_found_reason(observation)
        return ToolResult(
            success=False,
            message=reason,
            data={
                "type": "browser_action_result",
                "action": tool_name,
                "executed": False,
                "error": {
                    "type": "browser_target_not_found",
                    "arguments": arguments,
                    "message": reason,
                },
                "observation": observation,
                "target_resolution": {
                    "strategy": "semantic_element_ref",
                    "cached_element_count": len(self._last_browser_elements),
                },
            },
        )

    def _target_not_found_observation_context(self) -> dict[str, Any]:
        observation = self._last_browser_observation
        if not observation:
            return {}
        return {
            "url": observation.get("url"),
            "title": observation.get("title"),
            "public_summary": observation.get("public_summary"),
            "loading": observation.get("loading", False),
            "element_count": len(self._last_browser_elements),
            "link_count": len(observation.get("links") or []),
        }

    def _target_not_found_reason(self, observation: dict[str, Any]) -> str:
        title = str(observation.get("title") or "")
        public_summary = str(observation.get("public_summary") or "")
        page_text = f"{title}\n{public_summary}".lower()
        if (
            "just a moment" in page_text
            or "security verification" in page_text
            or "not a bot" in page_text
        ):
            return (
                "Browser action target was not found because the current page is "
                "showing a security verification screen instead of the requested site content."
            )
        if observation:
            return (
                "Browser action target was not found on the currently observed page. "
                "Observe the page or provide a clearer visible element name."
            )
        return (
            "Browser action target was not found. "
            "Observe the page or provide a clearer visible element name."
        )

    def _has_explicit_ref(self, arguments: dict[str, Any]) -> bool:
        value = arguments.get("ref")
        return isinstance(value, str) and bool(value.strip())

    def _shape_browser_action_arguments_for_mcp(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        accepted = self._mcp_parameter_names(tool_name)
        target_label = (
            arguments.get("element")
            or arguments.get("label")
            or arguments.get("name")
            or arguments.get("target")
            or arguments.get("selector")
            or arguments.get("ref")
        )
        target_ref = arguments.get("ref")
        target_value = target_ref or target_label

        shaped = dict(arguments)
        shaped.pop("target_resolution", None)
        shaped.pop("selector", None)
        shaped.pop("role", None)
        shaped.pop("label", None)
        shaped.pop("name", None)

        if target_label is not None:
            shaped.setdefault("element", str(target_label))
        if target_value is not None:
            shaped["target"] = str(target_value)

        if tool_name == "browser.click":
            shaped.pop("text", None)

        if not accepted:
            return shaped

        return {
            key: value
            for key, value in shaped.items()
            if key in accepted
        }

    def _mcp_parameter_names(self, tool_name: str) -> set[str]:
        definition = self._definitions.get(tool_name)
        if definition is None:
            return set()
        return {parameter.name for parameter in definition.parameters}

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
