from fastapi import APIRouter, HTTPException
from app.schemas.task_schema import TaskRequest, TaskResponse
from app.domain.services.task_service import TaskService

router = APIRouter(prefix="/internal/ai", tags=["Internal AI"])

task_service = TaskService()

@router.post("/tasks", response_model=TaskResponse)
async def internal_tasks(request: TaskRequest) -> TaskResponse:
    try:
        task = await task_service.run(request.message)
        
        return TaskResponse(
            task_id =task.id, 
            status=task.status,
            summary=task.summary,
            plan=task.plan,
            events=[event.model_dump(mode="json") for event in task.events],
            error=task.error
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Task agent failed: {str(e)}"
        )
    

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: str) -> TaskResponse:
    """
    List all tasks.
    """
    task = await task_service.get_task_by_id(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )
    
    return TaskResponse(
            task_id =task.id, 
            status=task.status,
            summary=task.summary,
            plan=task.plan,
            events=[event.model_dump(mode="json") for event in task.events],
            error=task.error
        )


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    """
    List all tasks.
    """
    tasks = await task_service.list_all_tasks()
    return [TaskResponse(
            task_id =task.id, 
            status=task.status,
            summary=task.summary,
            plan=task.plan,
            events=[event.model_dump(mode="json") for event in task.events],
            error=task.error
        ) for task in tasks]


@router.get("/tasks/{task_id}/events")
async def get_task_events(task_id: str):
    """
    Get all events for a task
    """

    events = await task_service.get_task_events(task_id)

    if events is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}",
        )
    
    events = [event.model_dump(mode="json") for event in events]

    return events