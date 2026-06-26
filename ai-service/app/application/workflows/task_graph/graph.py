from langgraph.graph import START, END, StateGraph

from app.application.workflows.task_graph.state import TaskGraphState

from app.application.workflows.task_graph.nodes import (
    TaskGraphNodes, 
    route_initial,
    route_after_plan,
    route_after_step,
    route_after_summary
)

def build_task_graph(nodes: TaskGraphNodes):
    graph = StateGraph(TaskGraphState)

    graph.add_node("create_plan", nodes.create_plan)
    graph.add_node("answer_directly", nodes.answer_directly)
    graph.add_node("execute_one_step", nodes.execute_one_step)
    graph.add_node("summarize", nodes.summarize)
    graph.add_node("complete_task", nodes.complete_task)
    graph.add_node("fail_task", nodes.fail_task)

    graph.add_conditional_edges(
        START,
        route_initial,
        {
            "direct_answer": "answer_directly",
            "plan": "create_plan",
        },
    )

    graph.add_edge("answer_directly", END)

    graph.add_conditional_edges(
        "create_plan",
        route_after_plan,
        {
            "execute": "execute_one_step",
            "failed": "fail_task",
        },
    )

    graph.add_conditional_edges(
        "execute_one_step",
        route_after_step,
        {
            "continue": "execute_one_step",
            "done": "summarize",
            "failed": "fail_task",
        },
    )

    graph.add_conditional_edges(
        "summarize",
        route_after_summary,
        {
            "complete": "complete_task",
            "failed": "fail_task"
        },
    )

    graph.add_edge("complete_task", END)
    graph.add_edge("fail_task", END)

    return graph.compile()
