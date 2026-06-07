
from app.domain.services.executor import Executor
from app.domain.services.planner import PlannerService
from app.domain.services.summarizer import Summarizer
from app.domain.services.task_state import TaskStateRecorder
from app.domain.models.task import TaskStatus

from app.application.workflows.task_graph.state import TaskGraphState



class TaskGraphNodes:
    def __init__(
            self,
            planner: PlannerService,
            executor: Executor,
            summarizer: Summarizer,
            state_recorder: TaskStateRecorder
    ) -> None:
        self.planner = planner
        self.executor = executor
        self.summarizer = summarizer
        self.state_recorder = state_recorder

    
    async def create_plan(self, state: TaskGraphState) -> dict:
        task = state["task"]

        try:
            plan = await self.planner.create_plan(task.message)
            self.state_recorder.plan_created(task, plan)
            self.state_recorder.task_running(task)

            return {
                "task": task,
                "error": None
            }
        except Exception as e:
            return {
                "task": task,
                "error": str(e)
            }
    

        
    async def execute_one_step(self, state: TaskGraphState) -> dict:
        task = state["task"]

        try:
            error = await self.executor.execute_next_step(task)

            return {
                "task": task,
                "error": error
            }
        except Exception as e:
            return {
                "task": task,
                "error": str(e)
            }


    async def summarize(self, state: TaskGraphState) -> dict:
        task = state["task"]

        try:
            summary = await self.summarizer.summarize(task)

            return {
                "task": task,
                "summary": summary,
                "error": None
            }
        except Exception as e:
            return {
                "task": task,
                "error": str(e)
            }



    async def complete_task(self, state: TaskGraphState) -> dict:
        task = state["task"]
        summary = state.get("summary") or ""

        self.state_recorder.plan_completed(task, summary)
        self.state_recorder.task_completed(task, summary)

        return {
            "task": task,
            "summary": summary,
            "error": None
        }


    async def fail_task(self, state: TaskGraphState) -> dict:
        task = state["task"]
        error = state.get("error") or task.error or "Task workflow failed."

        self.state_recorder.task_failed(task, error)

        return {
            "task": task,
            "error": error
        }


def route_after_plan(state: TaskGraphState) -> str:
        task = state["task"]
        
        if state.get("error") or task.status == TaskStatus.FAILED:
            return "failed"
        
        return "execute"


def route_after_step(state: TaskGraphState) -> str:
        task = state["task"]

        if state.get("error") or task.status == TaskStatus.FAILED:
            return "failed"
        
        if task.plan is not None and task.plan.get_next_step() is not None:
            return "continue"

        return "done"


def route_after_summary(state: TaskGraphState) -> str:
        if state.get("error"):
            return "failed"
        
        return "complete"