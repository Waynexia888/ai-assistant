import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[Any]] = set()

    def start(self, coro: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._on_done)

    def _on_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("Background task was cancelled.")
        except Exception:
            logger.exception("Background task failed.")

    def running_count(self) -> int:
        return len(self._tasks)
