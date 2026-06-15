import asyncio
from collections import defaultdict
from app.domain.models.event import Event


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict]]] = defaultdict(set)

    async def publish(self, task_id: str, event_seq: int, event: Event) -> None:
        payload = {
            "event_seq": event_seq,
            "event": event.model_dump(mode="json"),
        }

        for queue in list(self._subscribers.get(task_id, set())):
            await queue.put(payload)

    async def subscribe(self, task_id: str):
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._subscribers[task_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[task_id].discard(queue)