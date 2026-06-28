from openai import AsyncOpenAI

from app.core.config import settings
from app.domain.models.plan import Step
from app.domain.models.step_result import StepResult
from app.domain.models.task import Task



class Summarizer:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE or None,
        )
        self.model = settings.BASE_MODEL


    async def summarize(self, task: Task) -> str:
        if task.plan is None:
            return "Task has no plan."

        evidence: list[str] = []

        for index, step in enumerate(task.plan.steps, start=1):
            formatted = self._format_step_result(index, step)
            if formatted:
                evidence.append(formatted)

        if not evidence:
            return "No step results were generated."

        prompt = self._build_prompt(task, "\n\n".join(evidence))
        return await self._call_llm(prompt)
    

    def _format_step_result(self, index: int, step: Step) -> str:
        if step.result is None:
            return ""

        if step.result.type == "rag_search_result":
            return self._format_rag_result(index, step.result)

        if step.result.type == "llm_tool_calling_result":
            return self._format_llm_tool_calling_result(index, step, step.result)

        if step.result.type == "browser_observation_result":
            return self._format_browser_observation_result(index, step, step.result)

        content = step.result.content or str(step.result.data or "")

        if not content:
            return ""

        return (
            f"Step {index}: {step.description}\n"
            f"Result type: {step.result.type}\n"
            f"Result:\n{content}"
        )

    def _format_browser_observation_result(
        self,
        index: int,
        step: Step,
        result: StepResult,
    ) -> str:
        data = result.data if isinstance(result.data, dict) else {}
        observation = data.get("observation")
        observation = observation if isinstance(observation, dict) else {}
        public_summary = observation.get("public_summary")

        if not public_summary:
            public_summary = result.content or result.summary or ""

        return (
            f"Step {index}: {step.description}\n"
            "Result type: browser_observation_result\n"
            f"Page URL: {observation.get('url') or ''}\n"
            f"Page title: {observation.get('title') or ''}\n"
            "Public page evidence:\n"
            f"{self._truncate_browser_evidence(str(public_summary))}"
        )

    def _truncate_browser_evidence(
        self,
        value: str,
        max_length: int = 6000,
    ) -> str:
        if len(value) <= max_length:
            return value
        return f"{value[:max_length]}... [truncated]"

    def _format_llm_tool_calling_result(
        self,
        index: int,
        step: Step,
        result: StepResult,
    ) -> str:
        content = result.summary or result.content or ""

        if not content:
            return ""

        selected_evidence = self._format_selected_rag_evidence(result)
        trace_summary = self._format_tool_trace_summary(result)

        return (
            f"Step {index}: {step.description}\n"
            "Result type: llm_tool_calling_result\n"
            f"Completed step answer:\n{content}\n"
            f"Selected RAG evidence:\n{selected_evidence}\n"
            f"Tool trace summary:\n{trace_summary}"
        )

    def _format_selected_rag_evidence(self, result: StepResult) -> str:
        data = result.data if isinstance(result.data, dict) else {}
        traces = data.get("tool_traces", [])

        if not isinstance(traces, list):
            return "None"

        for trace in traces:
            if not isinstance(trace, dict):
                continue

            tool_call = trace.get("tool_call") or {}
            if tool_call.get("name") != "rag_search":
                continue

            rag_result = trace.get("result") or {}
            if not isinstance(rag_result, dict):
                continue

            selected_chunks = rag_result.get("selected_chunks")
            if rag_result.get("exact_title_match") and isinstance(selected_chunks, list) and selected_chunks:
                chunks_text = "".join(
                    self._format_rag_chunk(chunk_index, selected_chunk)
                    for chunk_index, selected_chunk in enumerate(selected_chunks, start=1)
                    if isinstance(selected_chunk, dict)
                )
                return (
                    "exact_title_match=true. Use selected_chunks only; "
                    "do not mix unselected retrieved chunks.\n"
                    f"{chunks_text}"
                )

        return "None"

    def _format_tool_trace_summary(self, result: StepResult) -> str:
        data = result.data if isinstance(result.data, dict) else {}
        traces = data.get("tool_traces", [])

        if not isinstance(traces, list) or not traces:
            return "No tools were called."

        lines = []
        for index, trace in enumerate(traces, start=1):
            if not isinstance(trace, dict):
                continue

            tool_call = trace.get("tool_call") or {}
            tool_name = tool_call.get("name") or "unknown"
            success = trace.get("success")
            status = "success" if success else "failed"

            lines.append(f"{index}. {tool_name}: {status}")

        return "\n".join(lines) if lines else "No tools were called."
    

    def _format_rag_result(self, index: int, result: StepResult) -> str:
        data = result.data if isinstance(result.data, dict) else {}
        chunks = data.get("chunks", [])

        if not chunks:
            return (
                f"Step {index}: RAG search evidence\n"
                "No relevant knowledge base chunks were found."
            )

        evidence_blocks = [
            self._format_rag_chunk(chunk_index, chunk)
            for chunk_index, chunk in enumerate(chunks, start=1)
        ]

        return (
            f"Step {index}: RAG search evidence\n"
            f"Search query: {data.get('query') or ''}\n"
            f"Found chunks: {len(chunks)}\n"
            "Evidence chunks are ordered by relevance. If selected_chunks are present, use selected_chunks only. Otherwise, use ranked chunks carefully.\n"
            f"{chr(10).join(evidence_blocks)}"
        )


    def _format_rag_chunk(self, index: int, chunk: dict) -> str:
        metadata = chunk.get("metadata") or {}
        title = chunk.get("title") or metadata.get("title") or "unknown"
        score = chunk.get("score")
        score_text = "" if score is None else f"{score:.4f}"

        return (
            f"\nTOP {index}\n"
            f"title: {title}\n"
            f"score: {score_text}\n"
            f"source: {chunk.get('source') or metadata.get('source') or 'unknown'}\n"
            f"source_name: {metadata.get('source_name') or ''}\n"
            f"asin: {metadata.get('asin') or ''}\n"
            f"rating: {metadata.get('rating') or ''}\n"
            f"content:\n{chunk.get('content') or ''}\n"
        )
    

    def _build_prompt(self, task: Task, evidence: str) -> str:
        return f"""
            You are the final summarizer for a task-based agent runtime.

            User task:
            {task.message}

            Execution evidence:
            {evidence}

            Rules:
            1. Produce the final answer for the user.
            2. Use RAG search evidence as knowledge-base evidence, not as the final answer by itself.
            3. Do not fabricate facts that are not supported by the provided evidence.
            4. If RAG evidence is empty or insufficient, say that the knowledge base did not contain enough relevant information.
            5. Preserve useful source information when it appears in the evidence.
            6. Reply in the same language as the user task.
            7. If the user asks to cite original evidence, include a short "原文证据" section with verbatim excerpt(s) copied from selected chunk content. Keep any English quote under 25 words.
            8. Do not translate quoted evidence. The explanation may be in the user's language, but quoted evidence must preserve the original source language and wording.
            9. Do not use ellipses inside quoted evidence unless the evidence itself contains ellipses.
            10. If selected RAG evidence is present, base the answer on selected_chunks only. If no selected evidence is present, use ranked chunks carefully and do not mix facts from different items.
            11. For RAG answers, prefer this structure when appropriate: "答案", "原文证据", "简短解释".
            12. Do not infer shipping, packaging, usage, or product-quality causes unless the selected evidence explicitly says so.
            13. If a step result has type="llm_tool_calling_result", use its completed step answer as evidence only when it does not conflict with selected RAG evidence.
            14. If selected RAG evidence says exact_title_match=true, treat selected_chunks as the only allowed source for the answer. Do not mix unselected retrieved chunks or completed-step claims that conflict with selected_chunks.
            15. Treat tool trace summaries as debugging context only. Do not expose raw JSON traces unless the user asks for debugging details.
            16. For browser observations, answer the user's intent using Public page evidence. Do not merely repeat the page title when headings or page details explain the product or website.
            17. Do not expose accessibility refs, raw snapshots, cookie banners, console logs, or artifact internals in the final answer unless the user explicitly asks for debugging details.
            """.strip()
    

    async def _call_llm(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You write final answers from task execution evidence.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        return response.choices[0].message.content or ""
