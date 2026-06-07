
from app.domain.models.task import Task
from app.domain.services.task_state import TaskStateRecorder
from app.application.workflows.task_graph.executor import LangGraphExecutor
from app.application.workflows.task_graph.factory import create_task_graph_executor

from app.infrastructure.repositories.in_memory_task_repository import InMemoryTaskRepository

from typing import Any

class TaskService:
    """
    Application service for task operations.

    Phase 1:
    - TaskService manually orchestrated the full task lifecycle:
      create task, create plan, execute steps, summarize, and complete the task.

    Phase 2:
    - TaskService delegates the task workflow to LangGraphExecutor.
    - LangGraph is responsible for workflow orchestration:
      planning, step execution, routing, summarization, completion, and failure handling.
    - TaskService stays focused on application-level responsibilities:
      creating the initial Task, recording the user message, saving task state,
      and exposing task query methods.

    This service does not implement graph node logic directly.
    It acts as the entry point between the API layer and the task workflow runtime.
    """
    def __init__(
        self,
        graph_executor: LangGraphExecutor | None = None,
        repository: InMemoryTaskRepository | None = None,
        state: TaskStateRecorder | None = None
    ) -> None:
        """
        Initialize TaskService dependencies.

        Dependencies:
        - state: records task, plan, step, tool, message, and done events.
        - graph_executor: runs the LangGraph task workflow.
        - repository: stores and retrieves Task objects.

        If dependencies are not provided, default in-memory/simple implementations
        are created for Phase 2 development and testing.
        """
        self.state = state or TaskStateRecorder()
        self.graph_executor = graph_executor or create_task_graph_executor(self.state)
        self.repository = repository or InMemoryTaskRepository()
        

    async def run(self, message: str) -> Task:
        """
        Create and run a task from a user message.

        Flow:
        1. Create a new Task from the user message.
        2. Record the initial user message event.
        3. Save the initial task.
        4. Delegate workflow execution to LangGraphExecutor.
        5. Save the final task after graph execution.
        6. Return the final Task.

        The LangGraph workflow is responsible for:
        - creating the plan
        - executing steps
        - routing between nodes
        - summarizing results
        - marking the task as completed or failed
        """

        task = Task(message=message)
        self.state.user_message(task, message)
        await self.repository.save(task)

        task = await self.graph_executor.execute(task)

        await self.repository.save(task)

        return task
        

    async def get_task_by_id(self, task_id: str) -> Task | None:
        """
        Get a task by id.

        Returns:
        - Task if found.
        - None if the task does not exist.
        """
        return await self.repository.get_task_by_id(task_id)
    

    async def list_all_tasks(self) -> list[Task]:
        """
        List all stored tasks.

        Phase 2 uses an in-memory repository, so this only returns tasks
        stored during the current application runtime.
        """

        return await self.repository.list_all_tasks()
    

    async def get_task_events(self, task_id: str) -> list[dict[str, Any]] | None:
        """
        Get all events for a task.

        Returns:
        - list of event dictionaries if the task exists.
        - None if the task does not exist.

        These events can be used by the API or frontend to display task progress,
        including user message, plan creation, step execution, tool calls,
        assistant message, errors, and done event.
        """
        task = await self.repository.get_task_by_id(task_id)
        if task is None:
            return None
        
        return task.events
        