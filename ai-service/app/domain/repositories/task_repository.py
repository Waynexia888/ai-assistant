from typing import Protocol

from app.domain.models.task import Task

class TaskRepository(Protocol):
    async def save(self, task: Task) -> Task:
        ...

    async def get_task_by_id(self, task_id: str) -> Task | None:
        ...

    async def list_all_tasks(self) -> list[Task]:
        ...

    async def delete(self, task_id: str) -> bool:
        ...


