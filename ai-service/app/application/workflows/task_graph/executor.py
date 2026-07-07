from app.domain.models.task import Task
from app.application.workflows.task_graph.state import TaskGraphState
from app.approvals.models import ApprovalRequest

class LangGraphExecutor:
    def __init__(self, graph) -> None:
        self.graph = graph

    async def execute(self, task: Task) -> Task:
        initial_state: TaskGraphState = {
            "task": task,
            "summary": None,
            "error": None,
            "route": None,
            "approval": None,
        }

        resultState = await self.graph.ainvoke(initial_state)
        return resultState["task"]

    async def resume(self, task: Task, approval: ApprovalRequest) -> Task:
        initial_state: TaskGraphState = {
            "task": task,
            "summary": None,
            "error": None,
            "route": "resume_approval",
            "approval": approval,
        }
        result_state = await self.graph.ainvoke(initial_state)
        return result_state["task"]
