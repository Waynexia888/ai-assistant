from app.domain.tools.registry import ToolRegistry
from app.domain.models.task import Task
from app.domain.models.plan import Step
from app.domain.models.tool_result import ToolResult
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.services.task_state import TaskStateRecorder

from typing import Any



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

        tool_name = "echo"
        arguments = self._build_tool_arguments(step)
 
        self.state.tool_calling(task, tool_name, arguments)
        tool_result = await self.tool_registry.invoke(tool_name, arguments)
        self.state.tool_called(task, tool_name, arguments, tool_result)

        if not tool_result.success:
            error = tool_result.message or f"Tool failed: {tool_name}"
            raise RuntimeError(error)
        
        result_text = self._get_result_text(tool_result)
        self.state.step_completed(task, step, result_text)

        

    def _build_tool_arguments(self, step: Step) -> dict[str, Any]:
        """
        Build tool arguments from a step.

        Current behavior:
        - Use the echo tool.
        - Pass the step description as the text argument.

        Later phases can replace this with real tool selection and
        structured tool arguments.
        """

        return {
            "text": step.description
        }


    def _get_result_text(self, tool_result: ToolResult[Any]) -> str:
        """
        Convert a ToolResult into plain text for step.result.

        Current behavior:
        - Store tool_result.data as a simple string.
        - Return an empty string when tool_result.data is None.
        """

        if tool_result.data is None:
            return ""
        
        return str(tool_result.data)
    

    async def execute_next_step(self, task: Task) -> str | None:
        """
        Phase 2 single-step executor for LangGraph.

        Execute only the next pending step in the task plan.

        Return value:
        - None means the step executed successfully, or there is no next step.
        - str means the step failed and the returned string is the error message.

        Behavior:
        - If the task has no plan, return an error message.
        - If there is no pending step, return None.
        - If the step succeeds, update the step state and return None.
        - If the step fails, mark only the step as failed and return the error.

        Important:
        - This method does not call task_failed().
        - This method does not decide whether the whole task should fail.
        - LangGraph receives the returned error and decides the next route:
          continue, retry, skip, summarize, or fail_task.
        """
        if task.plan is None:
            return "Task has no plan."
        
        step = task.plan.get_next_step()
        if step is None:
            return None
        
        try:
            await self._execute_step(task, step)
        except Exception as e:
            self.state.step_failed(task, step, str(e))
            return str(e)

        return None