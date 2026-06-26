from app.domain.tools.registry import ToolRegistry
from app.domain.models.task import Task
from app.domain.models.plan import Step
from app.domain.models.tool_result import ToolResult
from app.domain.models.step_execution import StepExecutionResult
from app.domain.tools.builtin import create_builtin_tool_registry
from app.domain.services.task_state import TaskStateRecorder
from app.domain.models.step_result import StepResult
from app.domain.llm.openai_provider import OpenAIChatProvider
from app.domain.llm.provider import LLMProvider
from app.domain.runtime.models import ToolCallingRuntimeResult
from app.domain.runtime.tool_calling_runtime import ToolCallingRuntime

from typing import Any
import asyncio
import json


DEFAULT_LLM_TOOL_CALLING_ALLOWED_TOOLS = [
    "rag_search",
    "text_stats",
    "calculator",
]


class Executor:
    """
    Executes task plan steps.

    Phase 1 role:
    - Execute the full task plan in a simple loop.
    - Stop when all steps are completed or when a step fails.
    - Mark the task as failed directly when a step/tool error happens.

    Phase 2 role:
    - Provide a single-step execution method for the LangGraph workflow.
    - Execute only one pending step at a time.
    - Mark step-level state changes through TaskStateRecorder.
    - Return step errors to LangGraph instead of deciding the final task status.

    Important design rule:
    - Step failure does not always mean task failure.
    - In Phase 2, LangGraph is responsible for deciding whether to continue,
      retry, skip, summarize, or fail the whole task.
    """
    def __init__(
        self, 
        tool_registry: ToolRegistry | None = None,
        state: TaskStateRecorder | None = None,
        llm_provider: LLMProvider | None = None,
        tool_calling_runtime: ToolCallingRuntime | None = None,
    ) -> None:
        self.tool_registry = tool_registry or create_builtin_tool_registry()
        self.state = state or TaskStateRecorder()
        self.llm_provider = llm_provider
        self.tool_calling_runtime = tool_calling_runtime


    async def execute(self, task: Task) -> Task:
        """
        Phase 1 full-plan executor.

        Execute all pending steps in the task plan.

        This method mutates the given task object directly and returns the same task.

        Behavior:
        - If the task has no plan, mark the whole task as failed.
        - Mark the task as running before step execution starts.
        - Execute pending steps one by one until no pending step remains.
        - If any step fails, mark both the step and the whole task as failed.
        - If all steps finish successfully, return the task without marking it completed.

        Note:
        - This method is kept for the Phase 1/manual workflow.
        - In the Phase 2 LangGraph workflow, prefer execute_next_step().
        - Final task completion, summary generation, assistant message event,
          and done event are handled by the caller or by LangGraph nodes.
        """

        if task.plan is None:
            self.state.task_failed(task, "Task has no plan.")
            return task
        
        self.state.task_running(task)

        while True:
            step = task.plan.get_next_step()

            if step is None:
                break

            try:
                await self._execute_step(task, step)
            except Exception as e:
                self.state.step_failed(task, step, str(e))
                self.state.task_failed(task, str(e))
                return task
        
        return task


    async def _execute_step(self, task: Task, step: Step) -> None:
        """
        Execute a single step with a built-in tool.

        Shared low-level step execution logic used by both:
        - Phase 1 execute()
        - Phase 2 execute_next_step()

        Behavior:
        - Mark the step as started.
        - Build tool arguments from the step description.
        - Call the selected tool.
        - Record tool calling and tool called events.
        - If the tool succeeds, write the tool output to step.result.
        - If the tool fails, raise an exception so the caller can decide
          how to handle the failure.

        This method only handles step/tool execution.
        It does not decide whether the whole task should fail.
        """

        self.state.step_started(task, step)
        # TEMPORARY TEST DELAY: remove after SSE/background-task testing.
        # await asyncio.sleep(5)

        if self._should_use_tool_calling_runtime(step):
            await self._execute_llm_tool_calling_step(task, step)
            return

        await self._execute_fixed_tool_step(task, step)

    async def _execute_fixed_tool_step(self, task: Task, step: Step) -> None:
        tool_name = self._select_tool_name(step) 
        arguments = self._build_tool_arguments(step)
 
        self.state.tool_calling(task, tool_name, arguments)
        tool_result = await self.tool_registry.invoke(tool_name, arguments)
        self.state.tool_called(task, tool_name, arguments, tool_result)

        if not tool_result.success:
            error = tool_result.message or f"Tool failed: {tool_name}"
            raise RuntimeError(error)
        
        # TEMPORARY TEST DELAY: remove after SSE/background-task testing.
        # await asyncio.sleep(5)
        step_result = self._build_step_result(tool_name, tool_result)
        self.state.step_completed(task, step, step_result)

    async def _execute_llm_tool_calling_step(self, task: Task, step: Step) -> None:
        runtime = self._get_tool_calling_runtime()
        allowed_tool_names = self._get_allowed_tool_names(step)
        runtime_result = await runtime.run(
            system_prompt=self._build_tool_runtime_system_prompt(),
            user_prompt=self._build_tool_runtime_user_prompt(
                task=task,
                step=step,
                allowed_tool_names=allowed_tool_names,
            ),
            allowed_tool_names=allowed_tool_names,
        )
        self._record_runtime_events(task, step, runtime_result)

        if runtime_result.stopped_reason == "runtime_error":
            raise RuntimeError(runtime_result.final_text or "Tool calling runtime failed.")

        step_result = self._build_runtime_step_result(runtime_result)
        self.state.step_completed(task, step, step_result)

    def _should_use_tool_calling_runtime(self, step: Step) -> bool:
        return not step.tool_name or step.tool_name == "llm_tool_calling"

    def _get_tool_calling_runtime(self) -> ToolCallingRuntime:
        if self.tool_calling_runtime is None:
            provider = self.llm_provider or OpenAIChatProvider()
            self.tool_calling_runtime = ToolCallingRuntime(
                llm_provider=provider,
                tool_registry=self.tool_registry,
            )

        return self.tool_calling_runtime

    def _get_allowed_tool_names(self, step: Step) -> list[str] | None:
        allowed_tools = step.tool_arguments.get("allowed_tools")
        registered_tools = set(self.tool_registry.list_tools())

        if isinstance(allowed_tools, list):
            filtered_tools = [
                str(tool_name)
                for tool_name in allowed_tools
                if str(tool_name).strip() and str(tool_name) in registered_tools
            ]

            if filtered_tools:
                return filtered_tools

        return [
            tool_name
            for tool_name in DEFAULT_LLM_TOOL_CALLING_ALLOWED_TOOLS
            if tool_name in registered_tools
        ]

    def _build_tool_runtime_system_prompt(self) -> str:
        return """
You are a task-based agent runtime.
You may call tools when they are useful.
Use tools only when they help complete the current step.
After reading tool results, produce a final answer for this step.
Do not fabricate tool results.
If a tool fails, explain the limitation and continue when possible.
""".strip()

    def _build_tool_runtime_user_prompt(
        self,
        task: Task,
        step: Step,
        allowed_tool_names: list[str] | None = None,
    ) -> str:
        previous_results = self._format_previous_step_results(task, step)
        available_tools = self._format_available_tools(allowed_tool_names)

        return f"""
Original user task:
{task.message}

Current step:
{step.description}

Step tool arguments and hints:
{self._format_step_tool_arguments(step)}

Available tools for this step:
{available_tools}

Previous step results:
{previous_results}

Complete the current step. Use tools when needed.
For rag_search, preserve exact titles, identifiers, punctuation, slashes, ampersands, and source-language keywords from the user task or query_hint.
If multiple RAG chunks look similar, prefer the chunk whose title exactly matches the requested title.
If a rag_search observation contains exact_title_match=true and selected_chunks, answer using selected_chunks only. Do not list, summarize, or infer from unselected retrieved chunks.
""".strip()

    def _format_step_tool_arguments(self, step: Step) -> str:
        if not step.tool_arguments:
            return "None"

        return json.dumps(step.tool_arguments, ensure_ascii=False, default=str)

    def _format_available_tools(self, allowed_tool_names: list[str] | None) -> str:
        tool_definitions = self.tool_registry.list_tool_definitions()
        allowed = set(allowed_tool_names) if allowed_tool_names is not None else None

        lines = []
        for tool in tool_definitions:
            if allowed is not None and tool.name not in allowed:
                continue

            lines.append(f"- {tool.name}: {tool.description}")

        return "\n".join(lines) if lines else "None"

    def _format_previous_step_results(self, task: Task, current_step: Step) -> str:
        if task.plan is None:
            return "None"

        blocks: list[str] = []
        for step in task.plan.steps:
            if step.id == current_step.id:
                break

            if step.result is None:
                continue

            result_text = step.result.summary or step.result.content or step.result.data
            blocks.append(
                f"- {step.description}: "
                f"{self._truncate_text(result_text)}"
            )

        return "\n".join(blocks) if blocks else "None"

    def _truncate_text(self, value: Any, max_length: int = 2000) -> str:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)

        if len(text) <= max_length:
            return text

        return f"{text[:max_length]}... [truncated]"

    def _record_runtime_events(
        self,
        task: Task,
        step: Step,
        runtime_result: ToolCallingRuntimeResult,
    ) -> None:
        for event in runtime_result.events:
            self.state.record_event(
                task=task,
                event_type=event.type,
                message=event.message,
                data={
                    "step_id": step.id,
                    **self._sanitize_runtime_event_data(event.data),
                },
            )

    def _sanitize_runtime_event_data(self, data: dict[str, Any]) -> dict[str, Any]:
        sensitive_keys = {
            "api_key",
            "authorization",
            "cookie",
            "password",
            "secret",
            "token",
        }

        sanitized: dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[redacted]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_runtime_event_data(value)
            else:
                sanitized[key] = value

        return sanitized
    
    def _select_tool_name(self, step: Step) -> str:
        return step.tool_name or "echo"
    

    def _build_tool_arguments(self, step: Step) -> dict[str, Any]:
        """
        Build tool arguments from a step.

        Current behavior:
        - Use the echo tool.
        - Pass the step description as the text argument.

        Later phases can replace this with real tool selection and
        structured tool arguments.
        """

        if step.tool_arguments:
            return dict(step.tool_arguments)
        
        if step.tool_name == "echo":
            return {"text": step.description}
        
        return {}
    

    async def execute_next_step(self, task: Task) -> StepExecutionResult:
        """
        Phase 3.1 single-step executor for LangGraph.

        Execute only the next pending step in the task plan.

        Return value:
        - StepExecutionResult.error is None when the step succeeds, or there is no next step.
        - StepExecutionResult.error contains the error message when the step fails.
        - StepExecutionResult.events contains only the events produced during this call.

        Important:
        - This method does not call task_failed().
        - This method does not decide whether the whole task should fail.
        - LangGraph receives result.error and decides the next route:
          continue, retry, skip, summarize, or fail_task.
        - Phase 4 can pass result.events directly to EventSink.
        """
        if task.plan is None:
            return StepExecutionResult(error="Task has no plan.")

        step = task.plan.get_next_step()
        if step is None:
            return StepExecutionResult()

        old_event_count = len(task.events)

        try:
            await self._execute_step(task, step)
        except Exception as e:
            self.state.step_failed(task, step, str(e))
            return StepExecutionResult(
                error=str(e),
                events=task.events[old_event_count:],
            )

        return StepExecutionResult(events=task.events[old_event_count:])


    def _build_step_result(self, tool_name: str, tool_result: ToolResult[Any]) -> StepResult:
        if tool_name == "rag_search" and isinstance(tool_result.data, dict):
            return StepResult(
                type="rag_search_result",
                content=tool_result.data.get("context"),
                data=tool_result.data,
                summary=f"Found {len(tool_result.data.get('chunks', []))} relevant chunks.",
                metadata={"tool_name": tool_name},
            )

        if isinstance(tool_result.data, str):
            return StepResult(
                type="text",
                content=tool_result.data,
                data=tool_result.data,
                metadata={"tool_name": tool_name},
            )

        return StepResult(
            type="tool_result",
            content=json.dumps(tool_result.data, ensure_ascii=False),
            data=tool_result.data,
            metadata={"tool_name": tool_name},
        )

    def _build_runtime_step_result(self, runtime_result: ToolCallingRuntimeResult) -> StepResult:
        final_text = runtime_result.final_text or self._build_runtime_result_fallback(runtime_result)

        return StepResult(
            type="llm_tool_calling_result",
            content=final_text,
            data={
                "stopped_reason": runtime_result.stopped_reason,
                "iterations": runtime_result.iterations,
                "tool_traces": [
                    trace.model_dump(mode="json")
                    for trace in runtime_result.tool_traces
                ],
            },
            summary=final_text,
            metadata={
                "tool_call_count": len(runtime_result.tool_traces),
                "stopped_reason": runtime_result.stopped_reason,
            },
        )

    def _build_runtime_result_fallback(self, runtime_result: ToolCallingRuntimeResult) -> str:
        return (
            "Tool calling runtime finished without a final text response. "
            f"Reason: {runtime_result.stopped_reason or 'unknown'}."
        )
