from datetime import datetime, timezone
from typing import Any
import asyncio
from copy import deepcopy

from app.approvals.models import (
    ApprovalAction,
    ApprovalAuditEntry,
    ApprovalRequest,
    ApprovalStatus,
)
from app.approvals.repository import ApprovalRepository
from app.domain.models.tool import ToolDefinition
from app.domain.tools.sanitizer import sanitize_tool_data


class ApprovalNotFoundError(LookupError):
    pass


class ApprovalAlreadyDecidedError(ValueError):
    pass


class ApprovalService:
    def __init__(self, repository: ApprovalRepository) -> None:
        self.repository = repository
        self._decision_lock = asyncio.Lock()

    async def create_request(
        self,
        *,
        task_id: str,
        step_id: str | None,
        session_id: str | None,
        tool: ToolDefinition,
        arguments: dict[str, Any],
        reason: str,
        user_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            task_id=task_id,
            step_id=step_id,
            session_id=session_id,
            action=ApprovalAction(
                tool_name=tool.name,
                arguments=sanitize_tool_data(arguments),
                risk_level=tool.risk_level,
                description=tool.description,
            ),
            execution_arguments=deepcopy(arguments),
            reason=reason,
            user_message=user_message,
            metadata=sanitize_tool_data(metadata or {}),
        )
        request.audit_trail.append(
            self._audit_entry(request, "approval_required")
        )
        return await self.repository.save(request)

    async def claim_approved_execution(
        self,
        *,
        approval_id: str,
        task_id: str,
        step_id: str | None,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> bool:
        async with self._decision_lock:
            request = await self.repository.get_by_id(approval_id)
            if (
                request is None
                or request.status != ApprovalStatus.APPROVED
                or request.execution_started_at is not None
            ):
                return False

            matches = (
                request.task_id == task_id
                and request.step_id == step_id
                and request.action.tool_name == tool_name
                and request.execution_arguments == arguments
            )
            if not matches:
                return False

            resumed_at = datetime.now(timezone.utc)
            request.execution_started_at = resumed_at
            request.resumed_at = resumed_at
            request.audit_trail.append(
                self._audit_entry(request, "approval_resumed")
            )
            await self.repository.save(request)
            return True

    async def record_execution_result(
        self,
        *,
        approval_id: str,
        success: bool,
        error: str | None,
        tool_trace_id: str,
    ) -> ApprovalRequest | None:
        async with self._decision_lock:
            request = await self.repository.get_by_id(approval_id)
            if request is None:
                return None

            request.completed_at = datetime.now(timezone.utc)
            request.execution_success = success
            request.execution_error = error
            request.execution_trace_id = tool_trace_id
            request.audit_trail.append(
                self._audit_entry(
                    request,
                    "approval_execution_completed",
                    success=success,
                    error=error,
                )
            )
            return await self.repository.save(request)

    async def get_request(self, approval_id: str) -> ApprovalRequest | None:
        return await self.repository.get_by_id(approval_id)

    async def list_pending(self) -> list[ApprovalRequest]:
        return await self.repository.list_by_status(ApprovalStatus.PENDING)

    async def approve(
        self,
        approval_id: str,
        *,
        decided_by: str,
        decision_note: str | None = None,
    ) -> ApprovalRequest:
        return await self._decide(
            approval_id,
            status=ApprovalStatus.APPROVED,
            decided_by=decided_by,
            decision_note=decision_note,
        )

    async def reject(
        self,
        approval_id: str,
        *,
        decided_by: str,
        decision_note: str | None = None,
    ) -> ApprovalRequest:
        return await self._decide(
            approval_id,
            status=ApprovalStatus.REJECTED,
            decided_by=decided_by,
            decision_note=decision_note,
        )

    async def _decide(
        self,
        approval_id: str,
        *,
        status: ApprovalStatus,
        decided_by: str,
        decision_note: str | None,
    ) -> ApprovalRequest:
        async with self._decision_lock:
            request = await self.repository.get_by_id(approval_id)
            if request is None:
                raise ApprovalNotFoundError(f"Approval request not found: {approval_id}")
            if request.status != ApprovalStatus.PENDING:
                raise ApprovalAlreadyDecidedError(
                    f"Approval request {approval_id} is already {request.status.value}."
                )

            request.status = status
            request.decided_at = datetime.now(timezone.utc)
            request.decided_by = decided_by
            request.decision_note = decision_note
            request.audit_trail.append(
                self._audit_entry(
                    request,
                    "approval_decided",
                    decided_by=decided_by,
                    decision_note=decision_note,
                )
            )
            return await self.repository.save(request)

    def _audit_entry(
        self,
        request: ApprovalRequest,
        event_type: str,
        *,
        decided_by: str | None = None,
        decision_note: str | None = None,
        success: bool | None = None,
        error: str | None = None,
    ) -> ApprovalAuditEntry:
        return ApprovalAuditEntry(
            trace_id=request.trace_id,
            type=event_type,
            status=request.status,
            task_id=request.task_id,
            step_id=request.step_id,
            tool_name=request.action.tool_name,
            risk_level=request.action.risk_level,
            decided_by=decided_by,
            decision_note=decision_note,
            success=success,
            error=error,
        )
