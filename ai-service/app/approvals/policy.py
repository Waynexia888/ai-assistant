from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.domain.models.tool import ToolDefinition, ToolRiskLevel


class ApprovalDecisionType(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class ApprovalPolicyDecision(BaseModel):
    type: ApprovalDecisionType
    reason: str
    user_message: str | None = None


class ApprovalPolicy:
    def evaluate(
        self,
        tool: ToolDefinition,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ApprovalPolicyDecision:
        del arguments, context

        if tool.metadata.get("disabled") or tool.metadata.get("approval_policy") == "deny":
            return ApprovalPolicyDecision(
                type=ApprovalDecisionType.DENY,
                reason=f"Tool {tool.name} is disabled by policy.",
            )

        if tool.risk_level == ToolRiskLevel.READ_ONLY:
            return ApprovalPolicyDecision(
                type=ApprovalDecisionType.ALLOW,
                reason="Read-only tool can run automatically.",
            )

        risk_label = getattr(tool.risk_level, "value", "unknown")
        return ApprovalPolicyDecision(
            type=ApprovalDecisionType.REQUIRE_APPROVAL,
            reason=f"Tool {tool.name} has {risk_label} risk and changes external state.",
            user_message=f"Agent wants to run {tool.name}. Please review before continuing.",
        )
