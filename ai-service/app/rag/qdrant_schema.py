from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType


RAG_FILTER_INDEXES: tuple[str, ...] = (
    "metadata.knowledge_base_id",
    "metadata.user_id",
)


def ensure_rag_payload_indexes(
    client: QdrantClient,
    collection_name: str,
) -> None:
    """
    Ensure payload indexes required by RAG filters exist.

    Qdrant can require keyword indexes for filtered vector search. Creating an
    existing index is harmless for this first version, so we keep this helper
    small and call it from both ingestion and retrieval paths.
    """

    collection_info = client.get_collection(collection_name)
    existing_schema = collection_info.payload_schema or {}

    for field_name in RAG_FILTER_INDEXES:
        if field_name in existing_schema:
            continue

        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD,
            wait=True,
        )
