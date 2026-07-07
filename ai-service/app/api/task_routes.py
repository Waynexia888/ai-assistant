import json
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.domain.models.task import Task, TaskStatus
from app.domain.services.task_service import TaskService
from app.schemas.task_schema import (
    TaskEventListResponse,
    TaskRequest,
    TaskResponse,
)

router = APIRouter(prefix="/internal/ai", tags=["Internal AI"])

task_service = TaskService()


def _compact_browser_observation(observation: dict[str, Any]) -> dict[str, Any]:
    elements = observation.get("elements")
    links = observation.get("links")
    return {
        "url": observation.get("url"),
        "title": observation.get("title"),
        "public_summary": observation.get("public_summary"),
        "screenshot": observation.get("screenshot"),
        "error": observation.get("error"),
        "loading": observation.get("loading", False),
        "element_count": len(elements) if isinstance(elements, list) else 0,
        "link_count": len(links) if isinstance(links, list) else 0,
    }


def _compact_observations(value: Any) -> Any:
    if isinstance(value, list):
        return [_compact_observations(item) for item in value]

    if not isinstance(value, dict):
        return value

    compacted = {
        key: _compact_observations(item)
        for key, item in value.items()
    }
    observation = compacted.get("observation")
    if isinstance(observation, dict):
        compacted["observation"] = _compact_browser_observation(observation)

    post_approval_screenshot = compacted.get("post_approval_screenshot")
    if isinstance(post_approval_screenshot, dict):
        compacted["post_approval_screenshot"] = _compact_browser_observation(
            post_approval_screenshot
        )

    return compacted


def _event_type(payload: dict) -> str:
    event = payload.get("event")
    if isinstance(event, dict):
        return event.get("type", "message")
    return "message"


def _task_response(task: Task, *, include_debug: bool = False) -> TaskResponse:
    events = [event.model_dump(mode="json") for event in task.events]
    if not include_debug:
        events = _compact_observations(events)

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        summary=task.summary,
        plan=task.plan,
        events=events,
        error=task.error,
        pending_approval_id=task.pending_approval_id,
    )


@router.post("/tasks", response_model=TaskResponse)
async def internal_tasks(request: TaskRequest) -> TaskResponse:
    try:
        task = await task_service.start_task(request.message)
        return _task_response(task)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Task agent failed: {str(e)}",
        )


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    tasks = await task_service.list_all_tasks()
    return [_task_response(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: str,
    include_debug: bool = False,
) -> TaskResponse:
    task = await task_service.get_task_by_id(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )

    return _task_response(task, include_debug=include_debug)


@router.get("/tasks/{task_id}/events", response_model=TaskEventListResponse)
async def get_task_events(
    task_id: str,
    after: int = 0,
    limit: int = 100,
    include_debug: bool = False,
) -> TaskEventListResponse:
    task = await task_service.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )

    rows = await task_service.list_task_events(task_id, after=after, limit=limit)
    if not include_debug:
        rows = _compact_observations(rows)
    next_cursor = rows[-1]["event_seq"] if rows else after

    return TaskEventListResponse(
        task_id=task_id,
        status=task.status.value,
        final_result=task.summary or (task.plan.result if task.plan else None),
        events=rows,
        next_cursor=next_cursor,
        done=task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        },
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    after: int = 0,
    include_debug: bool = False,
):
    task = await task_service.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )

    async def event_generator():
        historical_events = await task_service.list_task_events(task_id, after=after)
        if not include_debug:
            historical_events = _compact_observations(historical_events)
        for row in historical_events:
            yield {
                "event": _event_type(row),
                "id": str(row["event_seq"]),
                "data": json.dumps(row, ensure_ascii=False),
            }

        latest_task = await task_service.get_task_by_id(task_id)
        if latest_task is None or latest_task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            return

        async for payload in task_service.subscribe_task_events(task_id):
            if not include_debug:
                payload = _compact_observations(payload)
            yield {
                "event": _event_type(payload),
                "id": str(payload["event_seq"]),
                "data": json.dumps(payload, ensure_ascii=False),
            }

            if _event_type(payload) in {"done", "error", "task_cancelled"}:
                return

    return EventSourceResponse(event_generator())
