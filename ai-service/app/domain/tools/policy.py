from app.domain.models.tool import ToolRiskLevel


BROWSER_OBSERVATION_TOOL_NAMES = [
    "browser.open",
    "browser.observe",
    "browser.screenshot",
    "browser.extract_links",
]

BROWSER_RESERVED_ACTION_TOOL_NAMES = [
    "browser.click",
    "browser.type",
    "browser.submit",
]

DEFAULT_LLM_TOOL_CALLING_ALLOWED_TOOLS = [
    "rag_search",
    "text_stats",
    "calculator",
    *BROWSER_OBSERVATION_TOOL_NAMES,
]

DEFAULT_AUTO_TOOL_RISK_LEVELS = {
    ToolRiskLevel.READ_ONLY,
}
