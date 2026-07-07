from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.approvals.models import ApprovalRequest
from app.approvals.service import (
    ApprovalAlreadyDecidedError,
    ApprovalNotFoundError,
    ApprovalService,
)


router = APIRouter(prefix="/api/approvals", tags=["Approvals"])
_approval_service: ApprovalService | None = None
_resume_scheduler: Callable[[ApprovalRequest], Awaitable[None]] | None = None
_rejection_handler: Callable[[ApprovalRequest], Awaitable[None]] | None = None


class ApprovalDecisionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decision_note: str | None = Field(default=None, alias="decisionNote")
    decided_by: str = Field(default="user", alias="decidedBy")


def configure_approval_routes(
    service: ApprovalService,
    resume_scheduler: Callable[[ApprovalRequest], Awaitable[None]],
    rejection_handler: Callable[[ApprovalRequest], Awaitable[None]],
) -> None:
    global _approval_service, _resume_scheduler, _rejection_handler
    _approval_service = service
    _resume_scheduler = resume_scheduler
    _rejection_handler = rejection_handler


def _service() -> ApprovalService:
    if _approval_service is None:
        raise HTTPException(status_code=503, detail="Approval service is not configured.")
    return _approval_service


def _scheduler() -> Callable[[ApprovalRequest], Awaitable[None]]:
    if _resume_scheduler is None:
        raise HTTPException(status_code=503, detail="Approval resume scheduler is not configured.")
    return _resume_scheduler


def _reject_handler() -> Callable[[ApprovalRequest], Awaitable[None]]:
    if _rejection_handler is None:
        raise HTTPException(status_code=503, detail="Approval rejection handler is not configured.")
    return _rejection_handler


def _serialize(request: ApprovalRequest) -> dict[str, Any]:
    return request.model_dump(mode="json")


def _decision_response(request: ApprovalRequest, *, resume_required: bool) -> dict[str, Any]:
    return {
        "success": True,
        "data": {
            "approvalId": request.id,
            "status": request.status.value,
            "taskId": request.task_id,
            "resumeRequired": resume_required,
            "resumeScheduled": request.status.value == "approved",
        },
    }


@router.get("/pending")
async def list_pending_approvals() -> dict[str, Any]:
    requests = await _service().list_pending()
    return {"success": True, "data": [_serialize(request) for request in requests]}


@router.get("/{approval_id}")
async def get_approval(approval_id: str) -> dict[str, Any]:
    request = await _service().get_request(approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"Approval request not found: {approval_id}")
    return {"success": True, "data": _serialize(request)}


@router.post("/{approval_id}/approve")
async def approve_approval(
    approval_id: str,
    body: ApprovalDecisionBody,
) -> dict[str, Any]:
    try:
        request = await _service().approve(
            approval_id,
            decided_by=body.decided_by,
            decision_note=body.decision_note,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        await _scheduler()(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _decision_response(request, resume_required=False)


@router.post("/{approval_id}/reject")
async def reject_approval(
    approval_id: str,
    body: ApprovalDecisionBody,
) -> dict[str, Any]:
    try:
        request = await _service().reject(
            approval_id,
            decided_by=body.decided_by,
            decision_note=body.decision_note,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        await _reject_handler()(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _decision_response(request, resume_required=False)
