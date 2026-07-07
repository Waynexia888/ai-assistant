from app.domain.models.task import Task, TaskStatus
from app.domain.models.plan import Plan, Step, ExecutionStatus
from app.domain.models.tool_result import ToolResult
from app.domain.models.event import (
    Event,
    MessageEvent, 
    PlanEvent, 
    StepEvent,
    ToolEvent,
    RuntimeEvent,
    ApprovalEvent,
    DoneEvent,
    ErrorEvent,
)
from app.domain.models.step_result import StepResult
from app.domain.tools.sanitizer import sanitize_tool_data
from app.approvals.models import ApprovalRequest

from datetime import datetime, timezone
from typing import Any


class TaskStateRecorder:
    """
    Centralizes task / plan / step status changes and event recording.

    It does not execute business logic.
    It only mutates state and appends the matching event.
    """

    def _touch(self, task: Task) -> None:
        task.updated_at = datetime.now(timezone.utc)

    def _append_event(self, task: Task, event: Event) -> Event:
        task.events.append(event)
        self._touch(task)
        return event

    def user_message(self, task: Task, message: str) -> MessageEvent:
        event = MessageEvent(role="user", message=message)
        return self._append_event(task, event)

    def plan_created(self, task: Task, plan: Plan) -> PlanEvent:
        task.plan = plan
        event = PlanEvent(status="created", plan=plan.model_copy(deep=True))
        return self._append_event(task, event)

    def task_running(self, task: Task) -> None:
        task.status = TaskStatus.RUNNING
        if task.plan is not None:
            task.plan.status = ExecutionStatus.RUNNING
        self._touch(task)
        return None

    def task_pending_resume(self, task: Task, approval_id: str) -> RuntimeEvent:
        task.status = TaskStatus.PENDING_RESUME
        task.pending_approval_id = approval_id
        event = RuntimeEvent(
            event_type="approval_resume_scheduled",
            message="Approved action is scheduled to resume in the background.",
            data={"approval_id": approval_id},
        )
        return self._append_event(task, event)

    def task_resuming(
        self,
        task: Task,
        approval_id: str,
        approval_trace_id: str | None = None,
    ) -> RuntimeEvent:
        task.status = TaskStatus.RUNNING
        task.pending_approval_id = None
        if task.plan is not None:
            task.plan.status = ExecutionStatus.RUNNING
        resumed_event = ApprovalEvent(
            type="task_resumed",
            task_id=task.id,
            approval_id=approval_id,
            trace_id=approval_trace_id,
            message="Task resumed after approval.",
        )
        self._append_event(task, resumed_event)
        event = RuntimeEvent(
            event_type="approval_resume_started",
            message="Resuming the approved action.",
            data={"approval_id": approval_id},
        )
        return self._append_event(task, event)

    def approval_waiting(
        self,
        task: Task,
        step: Step,
        data: dict[str, Any],
    ) -> list[ApprovalEvent]:
        approval_id = str(data.get("approval_id") or "")
        common = {
            "task_id": task.id,
            "step_id": step.id,
            "approval_id": approval_id,
            "trace_id": data.get("approval_trace_id"),
            "tool_name": data.get("tool_name"),
            "risk_level": data.get("risk_level"),
        }
        events = [
            ApprovalEvent(
                type="approval_created",
                message="Approval request created.",
                data={
                    "arguments": sanitize_tool_data(data.get("arguments", {})),
                    "reason": data.get("reason"),
                },
                **common,
            ),
            ApprovalEvent(
                type="approval_required",
                message=str(data.get("user_message") or "Approval is required."),
                data={
                    "arguments": sanitize_tool_data(data.get("arguments", {})),
                    "reason": data.get("reason"),
                },
                **common,
            ),
        ]
        for event in events:
            self._append_event(task, event)
        return events

    def approval_approved(
        self,
        task: Task,
        approval: ApprovalRequest,
    ) -> ApprovalEvent:
        event = ApprovalEvent(
            type="approval_approved",
            task_id=task.id,
            step_id=approval.step_id,
            approval_id=approval.id,
            trace_id=approval.trace_id,
            tool_name=approval.action.tool_name,
            risk_level=approval.action.risk_level.value,
            decision_note=approval.decision_note,
            message="Approval request approved.",
        )
        return self._append_event(task, event)

    def step_started(self, task: Task, step: Step) -> StepEvent:
        step.status = ExecutionStatus.RUNNING
        event = StepEvent(status="started", step=step.model_copy(deep=True))
        return self._append_event(task, event)

    def tool_calling(
        self,
        task: Task,
        tool_name: str,
        arguments: dict[str, Any],
        trace: dict[str, Any] | None = None,
    ) -> ToolEvent:
        event = ToolEvent(
            status="calling",
            tool_name=tool_name,
            arguments=sanitize_tool_data(arguments),
            result=None,
            trace=trace,
        )
        return self._append_event(task, event)


    def tool_called(
        self,
        task: Task,
        tool_name: str,
        arguments: dict[str, Any],
        result: ToolResult[Any],
        trace: dict[str, Any] | None = None,
    ) -> ToolEvent:
        sanitized_result = result.model_copy(
            update={"data": sanitize_tool_data(result.data)},
            deep=True,
        )
        event = ToolEvent(
            status="called",
            tool_name=tool_name,
            arguments=sanitize_tool_data(arguments),
            result=sanitized_result,
            trace=trace,
        )
        return self._append_event(task, event)


    def record_event(
        self,
        task: Task,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        event = RuntimeEvent(
            event_type=event_type,
            message=message,
            data=data or {},
        )
        return self._append_event(task, event)

    
    def step_completed(self, task: Task, step: Step, result: StepResult) -> StepEvent:
        step.result = result
        step.status = ExecutionStatus.COMPLETED
        step.success = True
        step.error = None

        event = StepEvent(status="completed", step=step.model_copy(deep=True))
        return self._append_event(task, event)

    def step_paused(
        self,
        task: Task,
        step: Step,
        result: StepResult,
        approval_id: str,
    ) -> StepEvent:
        step.result = result
        step.status = ExecutionStatus.PAUSED
        step.success = False
        step.error = None
        task.status = TaskStatus.PAUSED
        task.pending_approval_id = approval_id
        if task.plan is not None:
            task.plan.status = ExecutionStatus.PAUSED

        event = StepEvent(status="paused", step=step.model_copy(deep=True))
        self._append_event(task, event)
        self._append_event(
            task,
            ApprovalEvent(
                type="task_paused",
                task_id=task.id,
                step_id=step.id,
                approval_id=approval_id,
                trace_id=(result.data or {}).get("approval_trace_id")
                if isinstance(result.data, dict)
                else None,
                tool_name=(result.data or {}).get("tool_name")
                if isinstance(result.data, dict)
                else None,
                risk_level=(result.data or {}).get("risk_level")
                if isinstance(result.data, dict)
                else None,
                message="Task paused while waiting for approval.",
            ),
        )
        return event

    def approval_rejected(
        self,
        task: Task,
        step: Step,
        approval: ApprovalRequest,
    ) -> list[Event]:
        result = StepResult(
            type="approval_rejected",
            content="You rejected the requested action. The task has been stopped.",
            summary="Approval rejected by user.",
            data={
                "approval_id": approval.id,
                "tool_name": approval.action.tool_name,
                "decision_note": approval.decision_note,
            },
        )
        step.result = result
        step.status = ExecutionStatus.REJECTED
        step.success = False
        step.error = None
        task.status = TaskStatus.CANCELLED
        task.pending_approval_id = None
        if task.plan is not None:
            task.plan.status = ExecutionStatus.CANCELLED

        events: list[Event] = [
            ApprovalEvent(
                type="approval_rejected",
                task_id=task.id,
                step_id=step.id,
                approval_id=approval.id,
                trace_id=approval.trace_id,
                tool_name=approval.action.tool_name,
                risk_level=approval.action.risk_level.value,
                decision_note=approval.decision_note,
                message="Approval request rejected; the tool was not executed.",
            ),
            StepEvent(status="rejected", step=step.model_copy(deep=True)),
            ApprovalEvent(
                type="task_cancelled",
                task_id=task.id,
                step_id=step.id,
                approval_id=approval.id,
                trace_id=approval.trace_id,
                tool_name=approval.action.tool_name,
                risk_level=approval.action.risk_level.value,
                decision_note=approval.decision_note,
                message="Task cancelled because the requested action was rejected.",
            ),
        ]
        for event in events:
            self._append_event(task, event)
        return events

    def approval_execution_completed(
        self,
        task: Task,
        step: Step,
        approval: ApprovalRequest,
        result: ToolResult[Any],
    ) -> ApprovalEvent:
        tool_trace = result.metadata.get("tool_trace") or {}
        event = ApprovalEvent(
            type="approval_execution_completed",
            task_id=task.id,
            step_id=step.id,
            approval_id=approval.id,
            trace_id=approval.trace_id,
            tool_name=approval.action.tool_name,
            risk_level=approval.action.risk_level.value,
            message=(
                "Approved tool action completed."
                if result.success
                else "Approved tool action failed."
            ),
            data={
                "success": result.success,
                "error": None if result.success else result.message,
                "tool_trace_id": tool_trace.get("trace_id"),
            },
        )
        return self._append_event(task, event)


    def step_failed(self, task: Task, step: Step, error: str) -> StepEvent:
        step.status = ExecutionStatus.FAILED
        step.success = False
        step.error = error

        event = StepEvent(status="failed", step=step.model_copy(deep=True))
        return self._append_event(task, event)



    def task_completed(self, task: Task, summary: str) -> list[Event]:
        task.status = TaskStatus.COMPLETED
        task.summary = summary
        self._touch(task)

        events: list[Event] = [
            MessageEvent(role="assistant", message=summary),
            DoneEvent(),
        ]

        task.events.extend(events)
        self._touch(task)
        return events
    


    def task_failed(self, task: Task, error: str) -> ErrorEvent:
        task.status = TaskStatus.FAILED
        task.error = error

        if task.plan is not None:
            task.plan.status = ExecutionStatus.FAILED
            task.plan.error = error

        event = ErrorEvent(error=error)
        return self._append_event(task, event)


    def plan_completed(self, task: Task, summary: str) -> PlanEvent | None:
        if task.plan is None:
            self._touch(task)
            return None

        task.plan.status = ExecutionStatus.COMPLETED
        task.plan.result = summary

        event = PlanEvent(
            status="completed",
            plan=task.plan.model_copy(deep=True),
        )
        return self._append_event(task, event)
