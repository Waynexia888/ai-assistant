
from .base import BaseTool
from app.domain.models.tool_result import ToolResult
from app.domain.tools.registry import ToolRegistry

from typing import Any



class EchoTool(BaseTool):
    name = "echo"
    description = "Return the input text directly. Useful for testing the tool pipeline."

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        text = arguments.get("text")

        if text is None:
            return ToolResult(success=False, message="Missing 'text' argument")
        
        return ToolResult(success=True, data=text)
    

def create_builtin_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    return registry
