from app.domain.models.task import Task, TaskStatus
from app.domain.models.plan import Plan, Step, ExecutionStatus
from app.domain.models.tool_result import ToolResult
from app.domain.models.event import (
    MessageEvent, 
    PlanEvent, 
    StepEvent,
    ToolEvent,
    ErrorEvent,
    DoneEvent
)

from typing import Any


class TaskStateRecorder:
    """
    Centralizes task / plan / step status changes and event recording.

    It does not execute business logic.
    It only mutates state and appends the matching event.
    """

    def user_message(self, task: Task, message: str) -> None:
        task.events.append(
            MessageEvent(role="user", message=message)
        )

    def plan_created(self, task: Task, plan: Plan) -> None:
        task.plan = plan
        task.events.append(
            PlanEvent(status="created", plan=plan.model_copy(deep=True))
        )

    def task_running(self, task: Task) -> None:
        task.status = TaskStatus.RUNNING
        if task.plan is not None:
            task.plan.status = ExecutionStatus.RUNNING

    def step_started(self, task: Task, step: Step) -> None:
        step.status = ExecutionStatus.RUNNING
        task.events.append(
            StepEvent(status="started", step=step.model_copy(deep=True))
        )


    def tool_calling(self, task: Task, tool_name: str, arguments: dict[str, Any]) -> None:
        task.events.append(
            ToolEvent(
                status="calling", 
                tool_name=tool_name, 
                arguments=dict(arguments), 
                result=None
            )
        )


    def tool_called(self, task: Task, tool_name: str, arguments: dict[str, Any], result: ToolResult[Any]) -> None:
        task.events.append(
            ToolEvent(
                status="called", 
                tool_name=tool_name, 
                arguments=dict(arguments), 
                result=result.model_copy(deep=True)
            )
        )

    def step_completed(self, task: Task, step: Step, result: str) -> None:
        step.result = result
        step.status = ExecutionStatus.COMPLETED
        step.success = True
        step.error = None
        task.events.append(
            StepEvent(status="completed", step=step.model_copy(deep=True))
        )


    def step_failed(self, task: Task, step: Step, error: str) -> None:
        # step.result = None
        step.status = ExecutionStatus.FAILED
        step.success = False
        step.error = error
        task.events.append(
            StepEvent(status="failed", step=step.model_copy(deep=True))
        )



    def task_completed(self, task: Task, summary: str) -> None:
        task.status = TaskStatus.COMPLETED
        task.summary = summary

        task.events.append(
            MessageEvent(role="assistant", message=summary)
        )
        task.events.append(DoneEvent())
        

    def task_failed(self, task: Task, error: str) -> None:
        task.status = TaskStatus.FAILED
        task.error = error

        if task.plan is not None:
            task.plan.status = ExecutionStatus.FAILED
            task.plan.error = error
        
        task.events.append(ErrorEvent(error=error))


    def plan_completed(self, task: Task, summary: str) -> None:
        if task.plan is not None:
            task.plan.status = ExecutionStatus.COMPLETED
            task.plan.result = summary

            task.events.append(
                PlanEvent(
                    status="completed",
                    plan=task.plan.model_copy(deep=True)
                )
            )

