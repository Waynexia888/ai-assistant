import asyncio
from typing import Any

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.rag.qdrant_schema import ensure_rag_payload_indexes
from app.rag.retrieval.formatter import format_chunks_as_context
from app.rag.retrieval.models import RAGChunk, RAGSearchResult


class RAGSearchService:
    """
    Query Qdrant and return relevant chunks.

    This service is retrieval-only:
    - It does not call a chat model.
    - It does not produce the final answer.
    - It lazily initializes Qdrant/OpenAI clients only when search() is called.
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        collection_name: str | None = None,
        max_top_k: int = 10,
    ) -> None:
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.max_top_k = max_top_k
        self._embedding: OpenAIEmbeddings | None = None
        self._qdrant_client: QdrantClient | None = None
        self._vector_store: QdrantVectorStore | None = None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        knowledge_base_id: str | None = None,
        user_id: str | None = "default",
        score_threshold: float | None = None,
    ) -> RAGSearchResult:
        """
        Search Qdrant for chunks relevant to the query.

        Args:
            query: User/task search query.
            top_k: Number of chunks to retrieve. Capped by max_top_k.
            knowledge_base_id: Optional metadata filter.
            user_id: Optional metadata filter. Defaults to "default" for the current first version.
            score_threshold: Optional minimum relevance score.

        Returns:
            RAGSearchResult with chunks and formatted context.
        """

        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")

        safe_top_k = self._normalize_top_k(top_k)
        vector_store = self._get_vector_store()
        qdrant_filter = self._build_filter(
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
        )

        search_top_k = min(self.max_top_k, max(safe_top_k, safe_top_k * 2))
        documents_with_scores = await asyncio.to_thread(
            vector_store.similarity_search_with_score,
            normalized_query,
            k=search_top_k,
            filter=qdrant_filter,
            score_threshold=score_threshold,
        )

        chunks = self._rerank_exact_title_matches(
            query=normalized_query,
            chunks=[
                self._document_to_chunk(document=document, score=score)
                for document, score in documents_with_scores
            ],
        )[:safe_top_k]

        return RAGSearchResult(
            query=normalized_query,
            chunks=chunks,
            context=format_chunks_as_context(chunks),
            collection_name=self.collection_name,
        )

    def _get_vector_store(self) -> QdrantVectorStore:
        if self._vector_store is None:
            self._embedding = OpenAIEmbeddings(
                model=self.embedding_model,
                api_key=settings.OPENAI_API_KEY,
            )
            self._qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            ensure_rag_payload_indexes(
                client=self._qdrant_client,
                collection_name=self.collection_name,
            )
            self._vector_store = QdrantVectorStore(
                client=self._qdrant_client,
                collection_name=self.collection_name,
                embedding=self._embedding,
            )

        return self._vector_store

    def _normalize_top_k(self, top_k: int) -> int:
        try:
            value = int(top_k)
        except (TypeError, ValueError):
            value = 5

        return max(1, min(value, self.max_top_k))

    def _build_filter(
        self,
        *,
        knowledge_base_id: str | None,
        user_id: str | None,
    ) -> Filter | None:
        conditions: list[FieldCondition] = []

        if knowledge_base_id:
            conditions.append(
                FieldCondition(
                    key="metadata.knowledge_base_id",
                    match=MatchValue(value=knowledge_base_id),
                )
            )

        if user_id:
            conditions.append(
                FieldCondition(
                    key="metadata.user_id",
                    match=MatchValue(value=user_id),
                )
            )

        if not conditions:
            return None

        return Filter(must=conditions)

    def _document_to_chunk(self, *, document: Any, score: float | None) -> RAGChunk:
        metadata = dict(getattr(document, "metadata", {}) or {})
        content = getattr(document, "page_content", "") or ""

        return RAGChunk(
            content=content,
            score=score,
            source=metadata.get("source"),
            title=metadata.get("title"),
            knowledge_base_id=metadata.get("knowledge_base_id"),
            user_id=metadata.get("user_id"),
            chunk_index=metadata.get("chunk_index"),
            metadata=metadata,
        )

    def _rerank_exact_title_matches(
        self,
        *,
        query: str,
        chunks: list[RAGChunk],
    ) -> list[RAGChunk]:
        query_text = query.casefold()

        def rank_key(item: tuple[int, RAGChunk]) -> tuple[int, int]:
            index, chunk = item
            title = (chunk.title or chunk.metadata.get("title") or "").strip()

            if title and title.casefold() in query_text:
                return (0, index)

            return (1, index)

        return [
            chunk
            for _, chunk in sorted(enumerate(chunks), key=rank_key)
        ]
