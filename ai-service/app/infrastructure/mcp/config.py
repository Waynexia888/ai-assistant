from pydantic import BaseModel, Field

from app.domain.models.tool import ToolRiskLevel


class MCPServerConfig(BaseModel):
    name: str
    enabled: bool = True
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    allowed_tools: set[str] | None = None
    tool_name_map: dict[str, str] = Field(default_factory=dict)
    tool_risk_levels: dict[str, ToolRiskLevel] = Field(default_factory=dict)
    default_risk_level: ToolRiskLevel = ToolRiskLevel.STATE_CHANGING

    def internal_tool_name(self, mcp_tool_name: str) -> str:
        return self.tool_name_map.get(mcp_tool_name, mcp_tool_name)

    def risk_level_for(self, mcp_tool_name: str) -> ToolRiskLevel:
        internal_name = self.internal_tool_name(mcp_tool_name)
        return self.tool_risk_levels.get(
            internal_name,
            self.tool_risk_levels.get(mcp_tool_name, self.default_risk_level),
        )


def create_playwright_mcp_config(
    *,
    enabled: bool,
    command: str = "npx",
    args: list[str] | None = None,
) -> MCPServerConfig:
    observation_tools = {
        "browser_navigate",
        "browser_snapshot",
        "browser_take_screenshot",
    }
    return MCPServerConfig(
        name="playwright",
        enabled=enabled,
        command=command,
        args=args or ["-y", "@playwright/mcp@latest", "--headless"],
        allowed_tools=observation_tools,
        tool_name_map={
            "browser_navigate": "browser.open",
            "browser_snapshot": "browser.observe",
            "browser_take_screenshot": "browser.screenshot",
        },
        tool_risk_levels={
            "browser.open": ToolRiskLevel.READ_ONLY,
            "browser.observe": ToolRiskLevel.READ_ONLY,
            "browser.screenshot": ToolRiskLevel.READ_ONLY,
        },
    )
