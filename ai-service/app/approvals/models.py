from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.models.tool import ToolRiskLevel


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalAction(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel
    description: str | None = None


class ApprovalAuditEntry(BaseModel):
    trace_id: str
    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ApprovalStatus
    task_id: str
    step_id: str | None = None
    tool_name: str
    risk_level: ToolRiskLevel
    decided_by: str | None = None
    decision_note: str | None = None
    success: bool | None = None
    error: str | None = None


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: f"approval_{uuid4()}")
    task_id: str
    step_id: str | None = None
    session_id: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    trace_id: str = Field(default_factory=lambda: f"approval-trace-{uuid4()}")
    action: ApprovalAction
    execution_arguments: dict[str, Any] = Field(
        default_factory=dict,
        exclude=True,
        repr=False,
    )
    reason: str
    user_message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_note: str | None = None
    execution_started_at: datetime | None = None
    resumed_at: datetime | None = None
    completed_at: datetime | None = None
    execution_success: bool | None = None
    execution_error: str | None = None
    execution_trace_id: str | None = None
    audit_trail: list[ApprovalAuditEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
