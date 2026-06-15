from typing import Protocol
from app.domain.models.event import Event


class EventPublisher(Protocol):
    async def publish(self, task_id: str, event_seq: int, event: Event) -> None:
        ...