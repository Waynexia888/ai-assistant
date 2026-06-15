from typing import Protocol

from app.domain.models.event import Event


class EventRepository(Protocol):
    async def append_event(self, task_id: str, event: Event) -> int:
        ...

    async def list_events(
        self,
        task_id: str,
        after: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        ...
