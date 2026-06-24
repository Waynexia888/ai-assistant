
from .base import BaseTool
from app.domain.models.tool_result import ToolResult
from app.domain.tools.registry import ToolRegistry
from app.domain.models.tool import ToolDefinition, ToolParameter
from app.domain.tools.rag_tools import RAGSearchTool

from typing import Any



class EchoTool(BaseTool):
    name = "echo"
    description = "Return the input text directly. Useful for testing the tool pipeline."

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name='text',
                    type='string',
                    description='Text to return.',
                    required=True
                )
            ]
        )
        

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        text = arguments.get("text")

        if text is None:
            return ToolResult(success=False, message="Missing 'text' argument")
        
        return ToolResult(success=True, data=text)




class TextStatsTool(BaseTool):
    name = "text_stats"
    description = "Count characters, words, and lines in a text."

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(name="text", type="string", description="Text to analyze.")
            ],
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult[dict[str, int]]:
        text = arguments.get("text")
        if text is None:
            return ToolResult(success=False, message="Missing 'text' argument")

        value = str(text)
        return ToolResult(
            success=True,
            data={
                "characters": len(value),
                "words": len(value.split()),
                "lines": len(value.splitlines()) or 1,
            },
        )



class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Calculate a simple math expression."

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Simple arithmetic expression, such as 1 + 2 * 3.",
                )
            ],
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult[str]:
        expression = arguments.get("expression")
        if expression is None:
            return ToolResult(success=False, message="Missing 'expression' argument")

        # 第三阶段可以先只返回表达式，确认工具路由正确。
        # 后面再补安全 AST 计算器。
        return ToolResult(success=True, data=f"calculator received: {expression}")




def create_builtin_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(TextStatsTool())
    registry.register(CalculatorTool())
    registry.register(RAGSearchTool())
    return registry





