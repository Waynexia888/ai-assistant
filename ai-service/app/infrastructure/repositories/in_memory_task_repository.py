from app.domain.models.task import Task
from typing import Optional

class InMemoryTaskRepository:
    def __init__(self):
        self._tasks: dict[str, Task] = {}

    async def save(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task
    
    async def get_task_by_Id(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
    
    async def list_all_tasks(self) -> list[Task]:
        return list(self._tasks.values())
    
    async def delete(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        
        del self._tasks[task_id]
        return True