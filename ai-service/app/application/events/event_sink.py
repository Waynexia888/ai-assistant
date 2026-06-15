from app.domain.models.event import Event
from app.domain.models.task import Task

RecordedEvents = Event | list[Event] | None


class EventSink:
    def __init__(self, event_repository, event_publisher, task_repository) -> None:
        self.event_repository = event_repository
        self.event_publisher = event_publisher
        self.task_repository = task_repository

    def _normalize(self, recorded: RecordedEvents) -> list[Event]:
        if recorded is None:
            return []

        if isinstance(recorded, list):
            return recorded

        return [recorded]

    async def commit(self, task: Task, recorded: RecordedEvents) -> None:
        events = self._normalize(recorded)

        for event in events:
            event_seq = await self.event_repository.append_event(task.id, event)
            await self.event_publisher.publish(task.id, event_seq, event)

        await self.task_repository.save(task)