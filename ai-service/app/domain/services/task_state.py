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
    ErrorEvent,
    DoneEvent
)
from app.domain.models.step_result import StepResult

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

    def step_started(self, task: Task, step: Step) -> StepEvent:
        step.status = ExecutionStatus.RUNNING
        event = StepEvent(status="started", step=step.model_copy(deep=True))
        return self._append_event(task, event)

    def tool_calling(
        self,
        task: Task,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolEvent:
        event = ToolEvent(
            status="calling",
            tool_name=tool_name,
            arguments=dict(arguments),
            result=None,
        )
        return self._append_event(task, event)


    def tool_called(
        self,
        task: Task,
        tool_name: str,
        arguments: dict[str, Any],
        result: ToolResult[Any],
    ) -> ToolEvent:
        event = ToolEvent(
            status="called",
            tool_name=tool_name,
            arguments=dict(arguments),
            result=result.model_copy(deep=True),
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
