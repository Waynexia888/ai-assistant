from app.domain.models.task import Task
from app.application.workflows.task_graph.state import TaskGraphState

class LangGraphExecutor:
    def __init__(self, graph) -> None:
        self.graph = graph

    async def execute(self, task: Task) -> Task:
        initial_state: TaskGraphState = {
            "task": task,
            "summary": None,
            "error": None,
            "route": None,
        }

        resultState = await self.graph.ainvoke(initial_state)
        return resultState["task"]
