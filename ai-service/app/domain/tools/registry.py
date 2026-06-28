
from app.domain.tools.base import BaseTool
from app.domain.models.tool_result import ToolResult
from app.domain.models.tool import ToolDefinition, ToolRiskLevel
from app.domain.models.tool_trace import ToolExecutionTrace
from app.domain.tools.sanitizer import sanitize_tool_data
from typing import Any
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4





class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}


    def register(self, tool: BaseTool, *, replace: bool = False) -> None:
        """
        Register a tool instance.
        """

        if tool.name in self._tools and not replace:
            raise ValueError(f"Tool already registered: {tool.name}")
        
        self._tools[tool.name] = tool


    def get_tool(self, name: str) -> BaseTool | None:
        """
        Get a tool by name.
        """

        return self._tools.get(name)
    

    def list_tools(
        self,
        risk_levels: set[ToolRiskLevel] | None = None,
    ) -> list[str]:
        """
        Return registered tool names, optionally filtered by risk level.
        """

        return [
            definition.name
            for definition in self.list_tool_definitions(risk_levels=risk_levels)
        ]
    

    def list_tool_definitions(
        self,
        risk_levels: set[ToolRiskLevel] | None = None,
    ) -> list[ToolDefinition]:
        definitions = [tool.definition for tool in self._tools.values()]

        if risk_levels is None:
            return definitions

        return [
            definition
            for definition in definitions
            if definition.risk_level in risk_levels
        ]
    


    def create_trace_id(self) -> str:
        return f"tool-call-{uuid4()}"

    def describe_invocation(
        self,
        name: str,
        arguments: dict[str, Any],
        trace_id: str,
    ) -> dict[str, Any]:
        tool = self.get_tool(name)
        definition = tool.definition if tool is not None else None
        metadata = definition.metadata if definition is not None else {}
        source = definition.source.value if definition is not None else "builtin"
        return {
            "trace_id": trace_id,
            "source": source,
            "mcp_server": metadata.get("mcp_server"),
            "internal_tool_name": name,
            "mcp_tool_name": metadata.get("mcp_tool_name"),
            "arguments": sanitize_tool_data(arguments),
        }

    async def invoke(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        trace_id: str | None = None,
    ) -> ToolResult:
        """
        Invoke a registered tool by name.
        """

        trace_id = trace_id or self.create_trace_id()
        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        tool = self.get_tool(name)

        if tool is None:
            result = ToolResult[Any](
                success=False, 
                message=f"Tool not found: {name}",
                data=None
            )
        else:
            try:
                result = await tool.invoke(arguments)
            # 写 try except，是为了防止
            # tool.invoke(arguments) 内部执行过程中报错，导致整个 Executor / API 直接崩掉。
            except Exception as e:
                result = ToolResult[Any](
                    success=False,
                    message=f"Tool execution failed: {str(e)}",
                    data=None,
                )

        return self.attach_trace(
            result=result,
            name=name,
            arguments=arguments,
            trace_id=trace_id,
            started_at=started_at,
            duration_ms=round((perf_counter() - started_clock) * 1000, 3),
        )

    def attach_trace(
        self,
        *,
        result: ToolResult[Any],
        name: str,
        arguments: dict[str, Any],
        trace_id: str,
        started_at: datetime,
        duration_ms: float,
    ) -> ToolResult[Any]:
        completed_at = datetime.now(timezone.utc)
        context = self.describe_invocation(name, arguments, trace_id)
        trace = ToolExecutionTrace(
            **context,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round(duration_ms, 3),
            success=result.success,
            result_type=self._result_type(result),
            error=None if result.success else result.message,
        )
        return result.model_copy(
            update={
                "metadata": {
                    **result.metadata,
                    "tool_trace": trace.model_dump(mode="json"),
                }
            }
        )

    def _result_type(self, result: ToolResult[Any]) -> str:
        if isinstance(result.data, dict):
            data_type = result.data.get("type")
            if data_type == "browser_observation":
                return "browser_observation_result"
            if isinstance(data_type, str) and data_type:
                return data_type
        return "tool_result" if result.success else "tool_error"
