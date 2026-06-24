from app.domain.tools.registry import ToolRegistry
from app.domain.models.task import Task
from app.domain.models.plan import Step
from app.domain.models.tool_result import ToolResult
from app.domain.models.step_execution import StepExecutionResult
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.services.task_state import TaskStateRecorder
from app.domain.models.step_result import StepResult

from typing import Any
import asyncio
import json



class Executor:
    """
    Executes task plan steps.

    Phase 1 role:
    - Execute the full task plan in a simple loop.
    - Stop when all steps are completed or when a step fails.
    - Mark the task as failed directly when a step/tool error happens.

    Phase 2 role:
    - Provide a single-step execution method for the LangGraph workflow.
    - Execute only one pending step at a time.
    - Mark step-level state changes through TaskStateRecorder.
    - Return step errors to LangGraph instead of deciding the final task status.

    Important design rule:
    - Step failure does not always mean task failure.
    - In Phase 2, LangGraph is responsible for deciding whether to continue,
      retry, skip, summarize, or fail the whole task.
    """
    def __init__(
        self, 
        tool_registry: ToolRegistry | None = None,
        state: TaskStateRecorder | None = None,
    ) -> None:
        self.tool_registry = tool_registry or create_builtin_tool_registry()
        self.state = state or TaskStateRecorder()


    async def execute(self, task: Task) -> Task:
        """
        Phase 1 full-plan executor.

        Execute all pending steps in the task plan.

        This method mutates the given task object directly and returns the same task.

        Behavior:
        - If the task has no plan, mark the whole task as failed.
        - Mark the task as running before step execution starts.
        - Execute pending steps one by one until no pending step remains.
        - If any step fails, mark both the step and the whole task as failed.
        - If all steps finish successfully, return the task without marking it completed.

        Note:
        - This method is kept for the Phase 1/manual workflow.
        - In the Phase 2 LangGraph workflow, prefer execute_next_step().
        - Final task completion, summary generation, assistant message event,
          and done event are handled by the caller or by LangGraph nodes.
        """

        if task.plan is None:
            self.state.task_failed(task, "Task has no plan.")
            return task
        
        self.state.task_running(task)

        while True:
            step = task.plan.get_next_step()

            if step is None:
                break

            try:
                await self._execute_step(task, step)
            except Exception as e:
                self.state.step_failed(task, step, str(e))
                self.state.task_failed(task, str(e))
                return task
        
        return task


    async def _execute_step(self, task: Task, step: Step) -> None:
        """
        Execute a single step with a built-in tool.

        Shared low-level step execution logic used by both:
        - Phase 1 execute()
        - Phase 2 execute_next_step()

        Behavior:
        - Mark the step as started.
        - Build tool arguments from the step description.
        - Call the selected tool.
        - Record tool calling and tool called events.
        - If the tool succeeds, write the tool output to step.result.
        - If the tool fails, raise an exception so the caller can decide
          how to handle the failure.

        This method only handles step/tool execution.
        It does not decide whether the whole task should fail.
        """

        self.state.step_started(task, step)
        # TEMPORARY TEST DELAY: remove after SSE/background-task testing.
        # await asyncio.sleep(5)

        tool_name = self._select_tool_name(step) 
        arguments = self._build_tool_arguments(step)
 
        self.state.tool_calling(task, tool_name, arguments)
        tool_result = await self.tool_registry.invoke(tool_name, arguments)
        self.state.tool_called(task, tool_name, arguments, tool_result)

        if not tool_result.success:
            error = tool_result.message or f"Tool failed: {tool_name}"
            raise RuntimeError(error)
        
        # TEMPORARY TEST DELAY: remove after SSE/background-task testing.
        # await asyncio.sleep(5)
        step_result = self._build_step_result(tool_name, tool_result)
        self.state.step_completed(task, step, step_result)
    
    def _select_tool_name(self, step: Step) -> str:
        return step.tool_name or "echo"
    

    def _build_tool_arguments(self, step: Step) -> dict[str, Any]:
        """
        Build tool arguments from a step.

        Current behavior:
        - Use the echo tool.
        - Pass the step description as the text argument.

        Later phases can replace this with real tool selection and
        structured tool arguments.
        """

        if step.tool_arguments:
            return dict(step.tool_arguments)
        
        if step.tool_name == "echo":
            return {"text": step.description}
        
        return {}
    

    async def execute_next_step(self, task: Task) -> StepExecutionResult:
        """
        Phase 3.1 single-step executor for LangGraph.

        Execute only the next pending step in the task plan.

        Return value:
        - StepExecutionResult.error is None when the step succeeds, or there is no next step.
        - StepExecutionResult.error contains the error message when the step fails.
        - StepExecutionResult.events contains only the events produced during this call.

        Important:
        - This method does not call task_failed().
        - This method does not decide whether the whole task should fail.
        - LangGraph receives result.error and decides the next route:
          continue, retry, skip, summarize, or fail_task.
        - Phase 4 can pass result.events directly to EventSink.
        """
        if task.plan is None:
            return StepExecutionResult(error="Task has no plan.")

        step = task.plan.get_next_step()
        if step is None:
            return StepExecutionResult()

        old_event_count = len(task.events)

        try:
            await self._execute_step(task, step)
        except Exception as e:
            self.state.step_failed(task, step, str(e))
            return StepExecutionResult(
                error=str(e),
                events=task.events[old_event_count:],
            )

        return StepExecutionResult(events=task.events[old_event_count:])


    def _build_step_result(self, tool_name: str, tool_result: ToolResult[Any]) -> StepResult:
        if tool_name == "rag_search" and isinstance(tool_result.data, dict):
            return StepResult(
                type="rag_search_result",
                content=tool_result.data.get("context"),
                data=tool_result.data,
                summary=f"Found {len(tool_result.data.get('chunks', []))} relevant chunks.",
                metadata={"tool_name": tool_name},
            )

        if isinstance(tool_result.data, str):
            return StepResult(
                type="text",
                content=tool_result.data,
                data=tool_result.data,
                metadata={"tool_name": tool_name},
            )

        return StepResult(
            type="tool_result",
            content=json.dumps(tool_result.data, ensure_ascii=False),
            data=tool_result.data,
            metadata={"tool_name": tool_name},
        )