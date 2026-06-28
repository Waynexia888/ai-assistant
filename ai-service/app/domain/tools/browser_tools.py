from typing import Any

from app.domain.models.tool import (
    ToolDefinition,
    ToolParameter,
    ToolRiskLevel,
)
from app.domain.models.tool_result import ToolResult
from app.domain.tools.base import BaseTool
from app.domain.tools.policy import BROWSER_OBSERVATION_TOOL_NAMES


class BrowserObservationTool(BaseTool):
    risk_level = ToolRiskLevel.READ_ONLY

    def __init__(
        self,
        name: str,
        description: str,
        parameters: list[ToolParameter] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self._parameters = parameters or []

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self._parameters,
            risk_level=self.risk_level,
            metadata={
                "capability": "browser_observation",
                "phase": "phase7_step1",
            },
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        return ToolResult(
            success=False,
            message=(
                f"Browser tool is defined but no MCP browser adapter is connected yet: {self.name}"
            ),
            data={
                "type": "browser_tool_unavailable",
                "tool_name": self.name,
                "arguments": arguments,
            },
        )


def create_browser_observation_tools() -> list[BrowserObservationTool]:
    tools = [
        BrowserObservationTool(
            name="browser.open",
            description="Open a URL in an external browser session and return a read-only page observation.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Absolute URL to open, such as https://example.com.",
                    required=True,
                ),
            ],
        ),
        BrowserObservationTool(
            name="browser.observe",
            description="Observe the current browser page without changing page state.",
        ),
        BrowserObservationTool(
            name="browser.screenshot",
            description="Capture a screenshot reference for the current browser page without changing page state.",
        ),
        BrowserObservationTool(
            name="browser.extract_links",
            description="Extract visible links from the current browser page without clicking them.",
        ),
    ]

    missing = set(BROWSER_OBSERVATION_TOOL_NAMES) - {tool.name for tool in tools}
    if missing:
        raise ValueError(f"Missing browser observation tool definitions: {sorted(missing)}")

    return tools
