from app.domain.tools.registry import ToolRegistry
from app.domain.models.task import Task
from app.domain.models.plan import Step
from app.domain.models.tool_result import ToolResult
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.services.task_state import TaskStateRecorder

from typing import Any



class Executor:
    """
    Executes a task plan step by step.

    Phase 1 responsibilities:
    - Read the next pending step from the task plan.
    - Execute one built-in tool for each step.
    - Write the tool output back to the step result.
    - Delegate task, step, and tool state updates to TaskStateRecorder.
    - Stop execution and mark the task as failed when a step or tool fails.

    This class does not generate the final summary.
    The caller is responsible for summarizing the task and marking it completed
    after all steps have been executed successfully.
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
        Execute all pending steps in the task plan.

        This method mutates the given task object directly and returns the same task.

        Behavior:
        - If the task has no plan, mark the task as failed.
        - Mark the task as running before step execution starts.
        - Execute pending steps one by one until no pending step remains.
        - If any step fails, mark both the step and task as failed, then stop.
        - If all steps finish successfully, return the task without marking it completed.

        The final task completion, summary generation, assistant message event,
        and done event are handled by the caller.
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

        Phase 1 behavior:
        - Mark the step as started.
        - Build tool arguments from the step description.
        - Call the selected tool.
        - Record tool calling and tool called events.
        - If the tool succeeds, write the tool output to step.result.
        - If the tool fails, raise an exception so execute() can handle failure.
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

        Phase 1 uses the echo tool, so the step description is passed as text.
        """

        return {
            "text": step.description
        }


    def _get_result_text(self, tool_result: ToolResult[Any]) -> str:
        """
        Convert a ToolResult into plain text for step.result.

        Phase 1 stores the tool result data as a simple string.
        """

        if tool_result.data is None:
            return ""
        
        return str(tool_result.data)
    
