from typing import TypedDict

from app.domain.models.task import Task
from app.approvals.models import ApprovalRequest

class TaskGraphState(TypedDict):
    """
    Phase 2 simple LangGraph state.

    For now, we keep the full Task object in state because the domain model
    already owns plan, steps, events, and task status.

    Later phases can split this into a more persistent/runtime-friendly state:
    task_id, current_step_index, step_result, events, summary, error, etc.
    """
    task: Task
    summary: str | None
    error: str | None
    route: str | None
    approval: ApprovalRequest | None
