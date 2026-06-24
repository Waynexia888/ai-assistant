import asyncio
from typing import List, Optional

from app.rag.ingestion.service import IngestionService

from langchain_community.document_loaders import WebBaseLoader


class URLProcessor:
    def __init__(
        self, 
        embedding_model: str | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 50,
        collection_name: str | None = None,
    ) -> None:
        self.ingestion_service = IngestionService(
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            collection_name=collection_name,
        )
        self.collection_name = self.ingestion_service.collection_name


    async def add_urls(
        self, 
        urls: List[str],
        knowledge_base_id: Optional[str] = None,
        user_id: Optional[str] = None,
        clean_before_chunking: bool = True,
    ) -> dict:
        """
        Load web pages from URLs, split them into chunks, embed them,
        and store them in Qdrant Cloud.
        """

        cleaned_urls = self._clean_urls(urls)

        if not cleaned_urls:
            return {
                "status": "error",
                "message": "No valid URLs provided.",
            }
        
        try:
            loader = WebBaseLoader(cleaned_urls)

            # WebBaseLoader.load() is synchronous, so run it in a thread
            # to avoid blocking the FastAPI event loop.
            documents = await asyncio.to_thread(loader.load)

            result = await self.ingestion_service.add_documents(
                documents=documents,
                source_type="url",
                content_type="url",
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                clean_before_chunking=clean_before_chunking,
                extra_metadata={"url_count": len(cleaned_urls)},
            )

            result["url_count"] = len(cleaned_urls)
            return result
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load URLs: {str(e)}",
            }

    def _clean_urls(self, urls: List[str]) -> List[str]:
        """
        Remove empty URLs and duplicate URLs.
        """
        seen = set()
        cleaned_urls = []

        for url in urls:
            url = url.strip()
            
            if not url:
                continue

            if not url.startswith(("http://", "https://")):
                continue

            if url in seen:
                continue

            seen.add(url)
            cleaned_urls.append(url)
        
        return cleaned_urls
