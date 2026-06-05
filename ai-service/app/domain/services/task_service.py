from app.domain.services.planner import PlannerService
from app.domain.services.executor import Executor
from app.domain.services.summarizer import Summarizer
from app.domain.models.task import Task, TaskStatus
from app.domain.services.task_state import TaskStateRecorder

from app.infrastructure.repositories.in_memory_task_repository import InMemoryTaskRepository

from typing import Any

class TaskService:
    """
    Orchestrates the full task lifecycle.

    Responsibilities:
    - Create a task from the user message.
    - Generate a plan.
    - Execute the plan.
    - Summarize the final step results.
    - Return the final task object.
    """
    def __init__(
        self,
        planner: PlannerService | None = None,
        executor: Executor | None = None,
        summarizer: Summarizer | None = None,
        repository: InMemoryTaskRepository | None = None,
        state: TaskStateRecorder | None = None
    ) -> None:
        self.state = state or TaskStateRecorder()
        self.planner = planner or PlannerService()
        self.executor = executor or Executor(state=self.state)
        self.summarizer = summarizer or Summarizer()
        self.repository = repository or InMemoryTaskRepository()
        

    async def run(self, message: str) -> Task:
        """
        Run the full task flow from user message to final task summary.
        """

        task = Task(message=message)
        self.state.user_message(task, message)
        await self.repository.save(task)

        try:
            plan = await self.planner.create_plan(message)
            self.state.plan_created(task, plan)
            await self.repository.save(task)

            task = await self.executor.execute(task)
            await self.repository.save(task)

            if task.status != TaskStatus.FAILED:
                summary = await self.summarizer.summarize(task)

                self.state.plan_completed(task, summary)
                self.state.task_completed(task, summary)
                await self.repository.save(task)

            return task
        except Exception as e:
            self.state.task_failed(task, str(e))

            await self.repository.save(task)
            return task
        

    async def get_task_by_Id(self, task_id: str) -> Task | None:
        """
        Get a task by id.
        """
        return await self.repository.get_task_by_Id(task_id)
    

    async def list_all_tasks(self) -> list[Task]:
        """
        List all tasks.
        """

        return await self.repository.list_all_tasks()
    

    async def get_task_events(self, task_id: str) -> list[dict[str, Any]] | None:
        """
        Get events for a task.
        """
        task = await self.repository.get_task_by_Id(task_id)
        if task is None:
            return None
        
        return task.events
        