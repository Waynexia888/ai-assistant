from app.rag.retrieval.models import RAGChunk


def format_chunks_as_context(chunks: list[RAGChunk]) -> str:
    """
    Format retrieved chunks into evidence text for later task steps or summarization.
    """

    blocks: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        source = chunk.source or "unknown"
        score = "" if chunk.score is None else f" score={chunk.score:.4f}"
        chunk_index = "" if chunk.chunk_index is None else f" chunk_index={chunk.chunk_index}"
        blocks.append(
            f"[{index}] source={source}{chunk_index}{score}\n"
            f"{chunk.content}"
        )

    return "\n\n".join(blocks)
