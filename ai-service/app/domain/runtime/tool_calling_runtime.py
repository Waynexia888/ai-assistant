import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.domain.llm.messages import LLMMessage, LLMToolCall
from app.domain.llm.provider import LLMProvider
from app.domain.models.tool import ToolDefinition
from app.domain.models.tool_result import ToolResult
from app.domain.runtime.models import (
    ToolCallingRuntimeResult,
    ToolRuntimeEvent,
    ToolTraceItem,
)
from app.domain.tools.registry import ToolRegistry
from app.domain.tools.sanitizer import sanitize_tool_data


class ToolCallingRuntime:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        max_iterations: int = 6,
        max_tool_calls: int = 12,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        allowed_tool_names: list[str] | None = None,
    ) -> ToolCallingRuntimeResult:
        result = ToolCallingRuntimeResult()
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        tools = self._get_allowed_tools(allowed_tool_names)
        total_tool_calls = 0

        try:
            for iteration in range(1, self.max_iterations + 1):
                result.iterations = iteration
                result.events.append(ToolRuntimeEvent(
                    type="llm_call_started",
                    message="Calling LLM with available tools.",
                    data={
                        "iteration": iteration,
                        "tool_names": [tool.name for tool in tools],
                    },
                ))

                llm_response = await self.llm_provider.complete(
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )

                assistant_message = llm_response.message
                messages.append(assistant_message)

                result.events.append(ToolRuntimeEvent(
                    type="llm_call_completed",
                    message="LLM call completed.",
                    data={
                        "iteration": iteration,
                        "finish_reason": llm_response.finish_reason,
                        "tool_call_count": len(assistant_message.tool_calls),
                        "usage": llm_response.usage,
                    },
                ))

                if not assistant_message.tool_calls:
                    result.final_message = assistant_message
                    result.final_text = assistant_message.content or ""
                    result.messages = messages
                    result.stopped_reason = "final_answer"
                    result.events.append(ToolRuntimeEvent(
                        type="runtime_completed",
                        message="Tool calling runtime completed with a final answer.",
                        data={
                            "iteration": iteration,
                            "stopped_reason": result.stopped_reason,
                        },
                    ))
                    return result

                for tool_call in assistant_message.tool_calls:
                    total_tool_calls += 1

                    if total_tool_calls > self.max_tool_calls:
                        result.messages = messages
                        result.stopped_reason = "max_tool_calls_reached"
                        result.final_text = self._build_stopped_message(result)
                        result.events.append(ToolRuntimeEvent(
                            type="runtime_failed",
                            message="Maximum tool calls reached.",
                            data={
                                "max_tool_calls": self.max_tool_calls,
                                "stopped_reason": result.stopped_reason,
                            },
                        ))
                        return result

                    tool_message, trace, events = await self._invoke_tool(
                        tool_call=tool_call,
                        allowed_tool_names=allowed_tool_names,
                    )
                    messages.append(tool_message)
                    result.tool_traces.append(trace)
                    result.events.extend(events)

                result.events.append(ToolRuntimeEvent(
                    type="runtime_iteration_completed",
                    message="Runtime iteration completed.",
                    data={
                        "iteration": iteration,
                        "total_tool_calls": total_tool_calls,
                    },
                ))

            result.messages = messages
            result.stopped_reason = "max_iterations_reached"
            result.final_text = self._build_stopped_message(result)
            result.events.append(ToolRuntimeEvent(
                type="runtime_failed",
                message="Maximum runtime iterations reached.",
                data={
                    "max_iterations": self.max_iterations,
                    "stopped_reason": result.stopped_reason,
                },
            ))
            return result
        except Exception as e:
            result.messages = messages
            result.stopped_reason = "runtime_error"
            result.final_text = f"Tool calling runtime failed: {str(e)}"
            result.events.append(ToolRuntimeEvent(
                type="runtime_failed",
                message="Tool calling runtime failed.",
                data={
                    "error": str(e),
                    "stopped_reason": result.stopped_reason,
                },
            ))
            return result

    def _get_allowed_tools(
        self,
        allowed_tool_names: list[str] | None,
    ) -> list[ToolDefinition]:
        definitions = self.tool_registry.list_tool_definitions()

        if allowed_tool_names is None:
            return definitions

        allowed = set(allowed_tool_names)
        return [
            definition
            for definition in definitions
            if definition.name in allowed
        ]

    async def _invoke_tool(
        self,
        tool_call: LLMToolCall,
        allowed_tool_names: list[str] | None,
    ) -> tuple[LLMMessage, ToolTraceItem, list[ToolRuntimeEvent]]:
        trace_id = self.tool_registry.create_trace_id()
        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        trace_context = self.tool_registry.describe_invocation(
            tool_call.name,
            tool_call.arguments,
            trace_id,
        )
        events = [
            ToolRuntimeEvent(
                type="tool_call_started",
                message=f"Calling tool: {tool_call.name}",
                data={
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.name,
                    **trace_context,
                },
            )
        ]

        invalid_arguments_message = self._validate_tool_call_arguments(tool_call)

        if allowed_tool_names is not None and tool_call.name not in allowed_tool_names:
            tool_result = self._build_tool_failure_result(
                message=(
                    f"Tool is not allowed for this runtime step: {tool_call.name}. "
                    f"Allowed tools: {', '.join(allowed_tool_names) or 'none'}"
                ),
                allowed_tool_names=allowed_tool_names,
            )
        elif invalid_arguments_message:
            tool_result = self._build_tool_failure_result(
                message=invalid_arguments_message,
                allowed_tool_names=allowed_tool_names,
            )
        elif self.tool_registry.get_tool(tool_call.name) is None:
            tool_result = self._build_tool_failure_result(
                message=(
                    f"Unknown tool: {tool_call.name}. "
                    f"Available tools: {', '.join(self.tool_registry.list_tools()) or 'none'}"
                ),
                allowed_tool_names=allowed_tool_names,
            )
        else:
            tool_result = await self.tool_registry.invoke(
                tool_call.name,
                tool_call.arguments,
                trace_id=trace_id,
            )

        if "tool_trace" not in tool_result.metadata:
            tool_result = self.tool_registry.attach_trace(
                result=tool_result,
                name=tool_call.name,
                arguments=tool_call.arguments,
                trace_id=trace_id,
                started_at=started_at,
                duration_ms=(perf_counter() - started_clock) * 1000,
            )

        event_type = "tool_call_completed" if tool_result.success else "tool_call_failed"
        events.append(ToolRuntimeEvent(
            type=event_type,
            message=tool_result.message or f"Tool call finished: {tool_call.name}",
            data={
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.name,
                "success": tool_result.success,
                "tool_trace": tool_result.metadata.get("tool_trace"),
            },
        ))

        trace = ToolTraceItem(
            tool_call=tool_call,
            success=tool_result.success,
            result=sanitize_tool_data(tool_result.data),
            error=None if tool_result.success else tool_result.message,
            execution_trace=tool_result.metadata.get("tool_trace"),
        )

        return self._tool_result_to_message(tool_call, tool_result), trace, events

    def _validate_tool_call_arguments(self, tool_call: LLMToolCall) -> str | None:
        if not isinstance(tool_call.arguments, dict):
            return (
                f"Invalid arguments for tool {tool_call.name}: "
                "arguments must be a JSON object."
            )

        if "_raw" in tool_call.arguments:
            return (
                f"Invalid arguments for tool {tool_call.name}: "
                f"could not parse JSON arguments: {tool_call.arguments['_raw']}"
            )

        return None

    def _build_tool_failure_result(
        self,
        message: str,
        allowed_tool_names: list[str] | None,
    ) -> ToolResult[dict[str, Any]]:
        return ToolResult(
            success=False,
            message=message,
            data={
                "type": "tool_error",
                "allowed_tools": allowed_tool_names or self.tool_registry.list_tools(),
            },
        )

    def _tool_result_to_message(
        self,
        tool_call: LLMToolCall,
        tool_result: ToolResult[Any],
    ) -> LLMMessage:
        data = self._build_observation_data(tool_result.data)
        payload = {
            "success": tool_result.success,
            "message": tool_result.message,
            "data": sanitize_tool_data(data),
        }

        return LLMMessage(
            role="tool",
            tool_call_id=tool_call.id,
            name=tool_call.name,
            content=json.dumps(payload, ensure_ascii=False, default=str),
        )

    def _build_observation_data(self, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if (
            data.get("type") == "rag_search_result"
            and data.get("exact_title_match")
            and isinstance(data.get("selected_chunks"), list)
            and data.get("selected_chunks")
        ):
            return {
                "type": data.get("type"),
                "query": data.get("query"),
                "collection_name": data.get("collection_name"),
                "exact_title_match": True,
                "selection_strategy": data.get("selection_strategy"),
                "answer_policy": data.get("answer_policy"),
                "selected_chunks": data.get("selected_chunks"),
            }

        return data

    def _build_stopped_message(self, result: ToolCallingRuntimeResult) -> str:
        return (
            "Tool calling runtime stopped before producing a final answer. "
            f"Reason: {result.stopped_reason}."
        )
