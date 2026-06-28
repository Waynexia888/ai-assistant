from app.application.events.event_sink import EventSink
from app.application.workflows.task_graph.executor import LangGraphExecutor
from app.application.workflows.task_graph.graph import build_task_graph
from app.application.workflows.task_graph.nodes import TaskGraphNodes
from app.domain.services.executor import Executor
from app.domain.services.direct_answer import DirectAnswerService
from app.domain.services.planner import PlannerService
from app.domain.services.summarizer import Summarizer
from app.domain.services.task_state import TaskStateRecorder
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.tools.registry import ToolRegistry


def create_task_graph_executor(
    state_recorder: TaskStateRecorder,
    event_sink: EventSink,
    tool_registry: ToolRegistry | None = None,
) -> LangGraphExecutor:
    tool_registry = tool_registry or create_builtin_tool_registry()

    planner = PlannerService(tool_registry=tool_registry)
    direct_answer = DirectAnswerService()
    executor = Executor(tool_registry=tool_registry, state=state_recorder)
    summarizer = Summarizer()

    nodes = TaskGraphNodes(
        direct_answer=direct_answer,
        planner=planner,
        executor=executor,
        summarizer=summarizer,
        state_recorder=state_recorder,
        event_sink=event_sink,
    )

    graph = build_task_graph(nodes)
    return LangGraphExecutor(graph)
