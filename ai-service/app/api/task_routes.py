import json

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


def _event_type(payload: dict) -> str:
    event = payload.get("event")
    if isinstance(event, dict):
        return event.get("type", "message")
    return "message"


def _task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        summary=task.summary,
        plan=task.plan,
        events=[event.model_dump(mode="json") for event in task.events],
        error=task.error,
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
async def get_task_by_id(task_id: str) -> TaskResponse:
    task = await task_service.get_task_by_id(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )

    return _task_response(task)


@router.get("/tasks/{task_id}/events", response_model=TaskEventListResponse)
async def get_task_events(
    task_id: str,
    after: int = 0,
    limit: int = 100,
) -> TaskEventListResponse:
    task = await task_service.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )

    rows = await task_service.list_task_events(task_id, after=after, limit=limit)
    next_cursor = rows[-1]["event_seq"] if rows else after

    return TaskEventListResponse(
        task_id=task_id,
        events=rows,
        next_cursor=next_cursor,
        done=task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED},
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_events(task_id: str, after: int = 0):
    task = await task_service.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )

    async def event_generator():
        historical_events = await task_service.list_task_events(task_id, after=after)
        for row in historical_events:
            yield {
                "event": _event_type(row),
                "id": str(row["event_seq"]),
                "data": json.dumps(row, ensure_ascii=False),
            }

        latest_task = await task_service.get_task_by_id(task_id)
        if latest_task is None or latest_task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
            return

        async for payload in task_service.subscribe_task_events(task_id):
            yield {
                "event": _event_type(payload),
                "id": str(payload["event_seq"]),
                "data": json.dumps(payload, ensure_ascii=False),
            }

            if _event_type(payload) in {"done", "error"}:
                return

    return EventSourceResponse(event_generator())
