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

        content = step.result.content or str(step.result.data or "")

        if not content:
            return ""

        return (
            f"Step {index}: {step.description}\n"
            f"Result type: {step.result.type}\n"
            f"Result:\n{content}"
        )
    

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
            "Evidence chunks are ordered by relevance. Prefer TOP 1 when it clearly matches the user's target.\n"
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
            7. If the user asks to cite original evidence, include a short "原文证据" section with an exact excerpt from the evidence. Keep any English quote under 25 words.
            8. Do not use ellipses inside quoted evidence unless the evidence itself contains ellipses.
            9. If TOP 1 clearly matches the requested title, rating, identifier, or key phrase, base the answer on TOP 1 only. Do not mix facts from lower-ranked chunks about different items.
            10. For RAG answers, prefer this structure when appropriate: "答案", "原文证据", "简短解释".
            11. Do not infer shipping, packaging, usage, or product-quality causes unless the selected evidence explicitly says so.
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
