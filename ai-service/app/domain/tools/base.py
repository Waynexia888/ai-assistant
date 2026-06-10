from abc import ABC, abstractmethod
from typing import Any
from app.domain.models.tool_result import ToolResult
from app.domain.models.tool import ToolDefinition



class BaseTool(ABC):
    """
    Base class for all tools.

    Every tool must have:
    - name: tool name used by ToolRegistry
    - description: short explanation for planner/executor
    - invoke(): actual execution logic
    """

    name: str
    description: str

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        pass
    

    # abstractmethod 强制子类必须实现这个方法，否则无法实例化。
    @abstractmethod
    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        """
        Execute the tool with arguments.

        Args:
            arguments: tool input arguments

        Returns:
            ToolResult
        """
        
        pass
