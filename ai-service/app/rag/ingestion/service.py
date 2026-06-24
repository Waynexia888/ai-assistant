import asyncio
import re
from pathlib import Path
from typing import Any

from app.core.config import settings

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.rag.ingestion.loaders import FileLoaderFactory
from app.rag.qdrant_schema import ensure_rag_payload_indexes


class IngestionService:
    """
    Shared ingestion pipeline for documents loaded from URLs, files, or other sources.
    """

    def __init__(
        self,
        embedding_model: str | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 50,
        collection_name: str | None = None,
    ) -> None:
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.embedding = OpenAIEmbeddings(
            model=embedding_model or settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self._ensure_collection_exists()
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embedding=self.embedding,
        )

    async def add_documents(
        self,
        documents: list[Document],
        source_type: str,
        content_type: str,
        source_name: str | None = None,
        knowledge_base_id: str | None = None,
        user_id: str | None = None,
        clean_before_chunking: bool = True,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not documents:
            return {
                "status": "warning",
                "message": "No documents found for ingestion.",
                "document_count": 0,
                "chunk_count": 0,
                "collection_name": self.collection_name,
            }

        try:
            processed_documents = self._prepare_documents(
                documents=documents,
                source_type=source_type,
                content_type=content_type,
                source_name=source_name,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                clean_before_chunking=clean_before_chunking,
                extra_metadata=extra_metadata,
            )

            chunks = self.splitter.split_documents(processed_documents)
            self._annotate_chunks(chunks)

            if not chunks:
                return {
                    "status": "warning",
                    "message": "Documents were loaded, but no chunks were generated.",
                    "document_count": len(documents),
                    "chunk_count": 0,
                    "collection_name": self.collection_name,
                }

            await asyncio.to_thread(self.vector_store.add_documents, chunks)

            return {
                "status": "success",
                "message": f"Successfully processed {len(chunks)} chunks from {len(documents)} document(s).",
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "collection_name": self.collection_name,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process documents: {str(e)}",
                "document_count": len(documents),
                "chunk_count": 0,
                "collection_name": self.collection_name,
            }

    def _prepare_documents(
        self,
        *,
        documents: list[Document],
        source_type: str,
        content_type: str,
        source_name: str | None,
        knowledge_base_id: str | None,
        user_id: str | None,
        clean_before_chunking: bool,
        extra_metadata: dict[str, Any] | None,
    ) -> list[Document]:
        processed_documents: list[Document] = []

        for doc in documents:
            if clean_before_chunking:
                doc.page_content = self._preprocess_text(doc.page_content)

            doc.metadata["content_type"] = content_type
            doc.metadata["source_type"] = doc.metadata.get("source_type", source_type)

            if source_name is not None:
                doc.metadata["source_name"] = source_name

            if knowledge_base_id is not None:
                doc.metadata["knowledge_base_id"] = knowledge_base_id

            if user_id is not None:
                doc.metadata["user_id"] = user_id

            if extra_metadata:
                doc.metadata.update(extra_metadata)

            processed_documents.append(doc)

        return processed_documents

    def _annotate_chunks(self, chunks: list[Document]) -> None:
        for index, chunk in enumerate(chunks):
            source_type = chunk.metadata.get("source_type", "document")
            chunk.metadata["chunk_index"] = index
            chunk.metadata["chunk_type"] = f"{source_type}_chunk"

    def _preprocess_text(self, text: str) -> str:
        text = text.strip()
        return re.sub(r"\s+", " ", text)

    def _ensure_collection_exists(self) -> None:
        collections = self.qdrant_client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if self.collection_name not in collection_names:
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,
                    distance=Distance.COSINE,
                ),
            )

        ensure_rag_payload_indexes(
            client=self.qdrant_client,
            collection_name=self.collection_name,
        )


class FileIngestionService:
    """
    Load local files with LangChain loaders, then pass Documents to IngestionService.
    """

    def __init__(
        self,
        ingestion_service: IngestionService | None = None,
        loader_factory: FileLoaderFactory | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or IngestionService()
        self.loader_factory = loader_factory or FileLoaderFactory()

    async def add_files(
        self,
        paths: list[str | Path],
        knowledge_base_id: str | None = None,
        user_id: str | None = None,
        clean_before_chunking: bool = True,
        batch_size: int = 1000,
    ) -> dict[str, Any]:
        if not paths:
            return {
                "status": "error",
                "message": "No files provided.",
                "file_count": 0,
                "document_count": 0,
                "chunk_count": 0,
            }

        total_documents = 0
        total_chunks = 0
        file_count = 0

        try:
            for path in paths:
                file_path = Path(path).expanduser().resolve()
                loader = self.loader_factory.create(file_path)
                source_type = self.loader_factory.source_type_for(file_path)

                file_result = await self._ingest_loaded_documents(
                    loader=loader,
                    file_path=file_path,
                    source_type=source_type,
                    knowledge_base_id=knowledge_base_id,
                    user_id=user_id,
                    clean_before_chunking=clean_before_chunking,
                    batch_size=batch_size,
                )

                if file_result.get("status") == "error":
                    return file_result

                total_documents += int(file_result.get("document_count", 0))
                total_chunks += int(file_result.get("chunk_count", 0))
                file_count += 1

            return {
                "status": "success" if total_chunks > 0 else "warning",
                "message": f"Successfully processed {total_chunks} chunks from {file_count} file(s).",
                "file_count": file_count,
                "document_count": total_documents,
                "chunk_count": total_chunks,
                "collection_name": self.ingestion_service.collection_name,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to ingest files: {str(e)}",
                "file_count": file_count,
                "document_count": total_documents,
                "chunk_count": 0,
            }

    async def _ingest_loaded_documents(
        self,
        *,
        loader: Any,
        file_path: Path,
        source_type: str,
        knowledge_base_id: str | None,
        user_id: str | None,
        clean_before_chunking: bool,
        batch_size: int,
    ) -> dict[str, Any]:
        total_documents = 0
        total_chunks = 0
        batch: list[Document] = []

        def add_file_metadata(documents: list[Document]) -> None:
            for doc in documents:
                doc.metadata.setdefault("source", str(file_path))
                doc.metadata["source_name"] = file_path.name
                doc.metadata["source_type"] = source_type

        if hasattr(loader, "lazy_load"):
            for doc in loader.lazy_load():
                batch.append(doc)

                if len(batch) >= batch_size:
                    add_file_metadata(batch)
                    result = await self.ingestion_service.add_documents(
                        documents=batch,
                        source_type="file",
                        content_type="file",
                        knowledge_base_id=knowledge_base_id,
                        user_id=user_id,
                        clean_before_chunking=clean_before_chunking,
                    )
                    if result.get("status") == "error":
                        return result

                    total_documents += int(result.get("document_count", 0))
                    total_chunks += int(result.get("chunk_count", 0))
                    batch = []

            if batch:
                add_file_metadata(batch)
                result = await self.ingestion_service.add_documents(
                    documents=batch,
                    source_type="file",
                    content_type="file",
                    knowledge_base_id=knowledge_base_id,
                    user_id=user_id,
                    clean_before_chunking=clean_before_chunking,
                )
                if result.get("status") == "error":
                    return result

                total_documents += int(result.get("document_count", 0))
                total_chunks += int(result.get("chunk_count", 0))
        else:
            loaded_documents = await asyncio.to_thread(loader.load)
            add_file_metadata(loaded_documents)
            result = await self.ingestion_service.add_documents(
                documents=loaded_documents,
                source_type="file",
                content_type="file",
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                clean_before_chunking=clean_before_chunking,
            )
            if result.get("status") == "error":
                return result

            total_documents += int(result.get("document_count", 0))
            total_chunks += int(result.get("chunk_count", 0))

        return {
            "status": "success" if total_chunks > 0 else "warning",
            "message": f"Successfully processed {total_chunks} chunks from {file_path.name}.",
            "file_count": 1,
            "document_count": total_documents,
            "chunk_count": total_chunks,
            "collection_name": self.ingestion_service.collection_name,
        }
