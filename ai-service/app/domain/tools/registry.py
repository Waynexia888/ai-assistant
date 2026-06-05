
from .base import BaseTool
from app.domain.models.tool_result import ToolResult
from typing import Any





class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool instance.
        """

        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        """
        Get a tool by name.
        """

        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """
        Return all registered tool names.
        """

        return list(self._tools.keys())

    async def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Invoke a registered tool by name.
        """

        tool = self.get_tool(name)

        if tool is None:
            return ToolResult(success=False, message=f"Tool not found: {name}")
        
        try:
            return await tool.invoke(arguments)
        # 写 try except，是为了防止
        # tool.invoke(arguments) 内部执行过程中报错，导致整个 Executor / API 直接崩掉。
        except Exception as e:
            return ToolResult[Any](
                success=False,
                message=f"Tool execution failed: {str(e)}",
                data=None,
            )