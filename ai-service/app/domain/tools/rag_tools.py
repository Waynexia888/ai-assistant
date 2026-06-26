from app.domain.models.tool import ToolDefinition, ToolParameter
from app.domain.tools.base import BaseTool
from app.domain.models.tool_result import ToolResult
from app.rag.retrieval.service import RAGSearchService

from typing import Any


class RAGSearchTool(BaseTool):
    name = "rag_search"
    description = "Search the local knowledge base and return relevant chunks as evidence."

    def __init__(self, search_service: RAGSearchService | None = None) -> None:
        self.search_service = search_service or RAGSearchService()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query for the local knowledge base.",
                    required=True,
                ),
                ToolParameter(
                    name="top_k",
                    type="integer",
                    description="Maximum number of chunks to retrieve. Defaults to 5.",
                    required=False,
                ),
                ToolParameter(
                    name="knowledge_base_id",
                    type="string",
                    description="Optional knowledge base id filter.",
                    required=False,
                ),
                ToolParameter(
                    name="score_threshold",
                    type="number",
                    description="Optional minimum relevance score threshold.",
                    required=False,
                ),
            ],
        )

    async def invoke(self, arguments: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        query = str(arguments.get("query") or "").strip()

        if not query:
            return ToolResult(
                success=False,
                message="Missing 'query' argument",
                data=None,
            )

        try:
            result = await self.search_service.search(
                query=query,
                top_k=self._parse_int(arguments.get("top_k"), default=5),
                knowledge_base_id=self._parse_optional_string(arguments.get("knowledge_base_id")),
                score_threshold=self._parse_optional_float(arguments.get("score_threshold")),
            )

            data = result.model_dump(mode="json")
            data["type"] = "rag_search_result"
            self._annotate_selected_chunks(data)

            return ToolResult(
                success=True,
                data=data,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"RAG search failed: {str(e)}",
                data=None,
            )

    def _parse_int(self, value: Any, *, default: int) -> int:
        if value is None:
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _parse_optional_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_optional_string(self, value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None

    def _annotate_selected_chunks(self, data: dict[str, Any]) -> None:
        chunks = data.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            data["exact_title_match"] = False
            data["selected_chunk"] = None
            data["selected_chunks"] = []
            data["selection_strategy"] = "none"
            data["answer_policy"] = "No chunks were found."
            return

        query = str(data.get("query") or "").casefold()
        selected_chunks = [
            chunk
            for chunk in chunks
            if self._chunk_title_exactly_matches_query(chunk, query)
        ]
        exact_title_match = bool(selected_chunks)

        data["exact_title_match"] = exact_title_match
        data["selected_chunks"] = selected_chunks
        data["selected_chunk"] = selected_chunks[0] if selected_chunks else None
        data["selection_strategy"] = (
            "exact_title_match"
            if exact_title_match
            else "ranked_chunks"
        )
        data["answer_policy"] = (
            "One or more retrieved chunk titles exactly match the query target. "
            "Answer using selected_chunks only; do not mix unselected retrieved chunks."
            if exact_title_match
            else "No exact title match was detected. Use the ranked chunks carefully."
        )

    def _chunk_title_exactly_matches_query(
        self,
        chunk: Any,
        query: str,
    ) -> bool:
        if not isinstance(chunk, dict):
            return False

        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        title = str(chunk.get("title") or metadata.get("title") or "").strip()
        return bool(title and title.casefold() in query)

    def _annotate_selected_chunk(self, data: dict[str, Any]) -> None:
        self._annotate_selected_chunks(data)
