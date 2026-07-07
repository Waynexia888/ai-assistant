
from app.domain.tools.base import BaseTool
from app.domain.models.tool_result import ToolResult
from app.domain.models.tool import ToolDefinition, ToolRiskLevel
from app.domain.models.tool_trace import ToolExecutionTrace
from app.domain.tools.sanitizer import sanitize_tool_data
from typing import Any
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from app.approvals.policy import (
    ApprovalDecisionType,
    ApprovalPolicy,
    ApprovalPolicyDecision,
)
from app.approvals.service import ApprovalService





class ToolRegistry:
    def __init__(
        self,
        approval_policy: ApprovalPolicy | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self._tools: dict[str, BaseTool] = {}
        self.approval_policy = approval_policy or ApprovalPolicy()
        self.approval_service = approval_service

    def configure_approval(
        self,
        *,
        policy: ApprovalPolicy,
        service: ApprovalService,
    ) -> None:
        self.approval_policy = policy
        self.approval_service = service


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
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        """
        Invoke a registered tool by name.
        """

        trace_id = trace_id or self.create_trace_id()
        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        invocation_context = context or {}
        approval_granted = False
        tool = self.get_tool(name)

        if tool is None:
            result = ToolResult[Any](
                success=False, 
                message=f"Tool not found: {name}",
                data=None
            )
        else:
            try:
                approval_granted = await self._is_approved_invocation(
                    tool=tool,
                    arguments=arguments,
                    context=invocation_context,
                )
                decision = (
                    ApprovalPolicyDecision(
                        type=ApprovalDecisionType.ALLOW,
                        reason="The exact tool invocation was approved by the user.",
                    )
                    if approval_granted
                    else self.approval_policy.evaluate(
                        tool.definition,
                        arguments,
                        invocation_context,
                    )
                )
                if decision.type == ApprovalDecisionType.DENY:
                    result = ToolResult[Any](
                        success=False,
                        message=decision.reason,
                        data={"type": "tool_denied", "reason": decision.reason},
                    )
                elif decision.type == ApprovalDecisionType.REQUIRE_APPROVAL:
                    result = await self._create_approval_required_result(
                        tool=tool,
                        arguments=arguments,
                        context=context or {},
                        trace_id=trace_id,
                        reason=decision.reason,
                        user_message=decision.user_message,
                    )
                else:
                    result = await tool.invoke(arguments)
            # 写 try except，是为了防止
            # tool.invoke(arguments) 内部执行过程中报错，导致整个 Executor / API 直接崩掉。
            except Exception as e:
                result = ToolResult[Any](
                    success=False,
                    message=f"Tool execution failed: {str(e)}",
                    data=None,
                )

            if (
                approval_granted
                and self.approval_service is not None
                and invocation_context.get("approval_id")
            ):
                await self.approval_service.record_execution_result(
                    approval_id=str(invocation_context["approval_id"]),
                    success=result.success,
                    error=None if result.success else result.message,
                    tool_trace_id=trace_id,
                )

        return self.attach_trace(
            result=result,
            name=name,
            arguments=arguments,
            trace_id=trace_id,
            started_at=started_at,
            duration_ms=round((perf_counter() - started_clock) * 1000, 3),
            approval_id=(
                str(invocation_context["approval_id"])
                if invocation_context.get("approval_id")
                else None
            ),
            approval_granted=approval_granted,
        )

    async def _is_approved_invocation(
        self,
        *,
        tool: BaseTool,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        approval_id = context.get("approval_id")
        if not context.get("approval_granted") or not approval_id:
            return False
        if self.approval_service is None or not context.get("task_id"):
            return False

        return await self.approval_service.claim_approved_execution(
            approval_id=str(approval_id),
            task_id=str(context["task_id"]),
            step_id=str(context["step_id"]) if context.get("step_id") else None,
            tool_name=tool.name,
            arguments=arguments,
        )

    async def _create_approval_required_result(
        self,
        *,
        tool: BaseTool,
        arguments: dict[str, Any],
        context: dict[str, Any],
        trace_id: str,
        reason: str,
        user_message: str | None,
    ) -> ToolResult[Any]:
        task_id = context.get("task_id")
        if self.approval_service is None or not task_id:
            return ToolResult(
                success=False,
                message="Risk-gated tool cannot run without an approval context.",
                data={"type": "tool_denied", "reason": reason},
            )

        approval = await self.approval_service.create_request(
            task_id=str(task_id),
            step_id=str(context["step_id"]) if context.get("step_id") else None,
            session_id=str(context["session_id"]) if context.get("session_id") else None,
            tool=tool.definition,
            arguments=arguments,
            reason=reason,
            user_message=user_message or f"Please review {tool.name} before continuing.",
            metadata={
                "trace_id": trace_id,
                "tool_call_id": context.get("tool_call_id"),
                "mcp_server": tool.definition.metadata.get("mcp_server"),
                "browser_url": context.get("browser_url"),
            },
        )
        return ToolResult(
            success=False,
            message=approval.user_message,
            data={
                "type": "approval_required",
                "approval_id": approval.id,
                "approval_trace_id": approval.trace_id,
                "tool_name": tool.name,
                "risk_level": tool.definition.risk_level.value,
                "arguments": sanitize_tool_data(arguments),
                "reason": reason,
                "user_message": approval.user_message,
            },
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
        approval_id: str | None = None,
        approval_granted: bool = False,
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
            approval_id=approval_id,
            approval_granted=approval_granted,
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
