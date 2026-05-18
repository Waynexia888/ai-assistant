import os
import re
import asyncio
from typing import List, Optional

from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv


class URLProcessor:
    def __init__(
        self, 
        embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        chunk_size: int = 800,
        chunk_overlap: int = 50,
        collection_name: str = os.getenv("QDRANT_COLLECTION", "ai_assistant_rag"),
    ) -> None:
        self.collection_name = collection_name

        self.embedding = OpenAIEmbeddings(
            model=embedding_model, 
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )

        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )

        self._ensure_collection_exists()
        
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embedding=self.embedding
        )


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

            return await self._process_documents(
                documents=documents,
                source_urls=cleaned_urls,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                clean_before_chunking=clean_before_chunking
            )
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load URLs: {str(e)}",
            }
        

    async def _process_documents(
        self, 
        documents: List[Document],
        source_urls: List[str],
        knowledge_base_id: Optional[str] = None,
        user_id: Optional[str] = None,
        clean_before_chunking: bool = True,
    ) -> dict:
        
        if not documents:
            return {
                "status": "warning",
                "message": "No documents found at the provided URLs.",
            }

        
        try:
            processed_documents: List[Document] = []

            for doc in documents:
                if clean_before_chunking:
                    doc.page_content = self._preprocess_text(doc.page_content)

                doc.metadata["content_type"] = 'url'

                if knowledge_base_id is not None:
                    doc.metadata["knowledge_base_id"] = knowledge_base_id
                
                if user_id is not None:
                    doc.metadata["user_id"] = user_id

                processed_documents.append(doc)
                
            chunks = self.splitter.split_documents(processed_documents)

            for index, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = index
                chunk.metadata["chunk_type"] = "web_page_chunk" 

            if not chunks:
                return {
                    "status": "warning",
                    "message": "Documents were loaded, but no chunks were generated.",
                    "url_count": len(source_urls),
                    "chunk_count": 0,
                }

            # vector_store.add_documents() is also synchronous.
            # It will call the embedding model and store vectors in Qdrant.
            await asyncio.to_thread(self.vector_store.add_documents, chunks)

            return {
                "status": "success",
                "message": f"Successfully processed {len(chunks)} chunks from {len(source_urls)} URL(s).",
                "url_count": len(source_urls),
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "collection_name": self.collection_name,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process documents: {str(e)}",
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
    
    def _preprocess_text(self, text: str) -> str:
        """
        Basic preprocessing before chunking.
        You can improve this later by removing headers, footers,
        navigation text, ads, or duplicated content.
        """

        text = text.strip()

        # Replace multiple spaces/newlines with a single space.
        text = re.sub(r"\s+", " ", text)

        return text
    
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