from collections.abc import AsyncIterator
from typing import Any

from app.application.background.task_manager import BackgroundTaskManager
from app.application.events.event_sink import EventSink
from app.application.events.in_memory_event_publisher import InMemoryEventPublisher
from app.application.workflows.task_graph.executor import LangGraphExecutor
from app.application.workflows.task_graph.factory import create_task_graph_executor
from app.domain.repositories.event_repository import EventRepository
from app.domain.repositories.task_repository import TaskRepository
from app.domain.models.task import Task
from app.domain.services.task_state import TaskStateRecorder
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.tools.registry import ToolRegistry
from app.infrastructure.repositories.postgres_event_repository import PostgresEventRepository
from app.infrastructure.repositories.postgres_task_repository import PostgresTaskRepository


class TaskService:
    """Application service for the task-based agent runtime.

    Phase 4 responsibilities:
    - create task runtime records
    - start LangGraph execution in the background
    - persist task / plan / step snapshots through the repository
    - persist and publish runtime events through EventSink
    - expose event history and SSE subscription helpers
    """

    def __init__(
        self,
        graph_executor: LangGraphExecutor | None = None,
        repository: TaskRepository | None = None,
        event_repository: EventRepository | None = None,
        event_publisher: InMemoryEventPublisher | None = None,
        state: TaskStateRecorder | None = None,
        background_tasks: BackgroundTaskManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.state = state or TaskStateRecorder()
        self.repository = repository or PostgresTaskRepository()
        self.event_repository = event_repository or PostgresEventRepository()
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        self.background_tasks = background_tasks or BackgroundTaskManager()
        self.tool_registry = tool_registry or create_builtin_tool_registry()
        self.event_sink = EventSink(
            event_repository=self.event_repository,
            event_publisher=self.event_publisher,
            task_repository=self.repository,
        )
        self.graph_executor = graph_executor or create_task_graph_executor(
            self.state,
            self.event_sink,
            tool_registry=self.tool_registry,
        )

    async def create_task(self, message: str) -> Task:
        task = Task(message=message)

        # Save the task first so agent.events can reference agent.tasks(task.id).
        await self.repository.save(task)

        event = self.state.user_message(task, message)
        await self.event_sink.commit(task, event)

        return task

    async def start_task(self, message: str) -> Task:
        task = await self.create_task(message)
        self.background_tasks.start(self.run_task(task.id))
        return task

    async def run_task(self, task_id: str) -> Task | None:
        task = await self.repository.get_task_by_id(task_id)
        if task is None:
            return None

        try:
            task = await self.graph_executor.execute(task)
            await self.repository.save(task)
            return task
        except Exception as exc:
            event = self.state.task_failed(task, str(exc))
            await self.event_sink.commit(task, event)
            return task

    async def run(self, message: str) -> Task:
        task = await self.create_task(message)
        result = await self.run_task(task.id)
        if result is None:
            raise RuntimeError(f"Task disappeared before execution: {task.id}")
        return result

    async def get_task_by_id(self, task_id: str) -> Task | None:
        return await self.repository.get_task_by_id(task_id)

    async def list_all_tasks(self) -> list[Task]:
        return await self.repository.list_all_tasks()

    async def list_task_events(
        self,
        task_id: str,
        after: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return await self.event_repository.list_events(
            task_id=task_id,
            after=after,
            limit=limit,
        )

    async def get_task_events(self, task_id: str) -> list[dict[str, Any]] | None:
        task = await self.repository.get_task_by_id(task_id)
        if task is None:
            return None

        return await self.list_task_events(task_id)

    async def subscribe_task_events(self, task_id: str) -> AsyncIterator[dict[str, Any]]:
        async for payload in self.event_publisher.subscribe(task_id):
            yield payload
