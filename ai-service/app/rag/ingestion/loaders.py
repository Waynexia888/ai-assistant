import json
from pathlib import Path
from typing import Any

from app.core.config import settings

from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader

_ = settings.USER_AGENT


class FileLoaderFactory:
    """
    Create LangChain document loaders for supported local file types.

    Heavy optional dependencies are imported lazily so the FastAPI app can
    still start when, for example, PDF/DOCX support is not installed yet.
    """

    SUPPORTED_TEXT_SUFFIXES = {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
    }

    def create(self, path: str | Path) -> Any:
        file_path = Path(path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader

            return PyPDFLoader(str(file_path))

        if suffix == ".docx":
            from langchain_community.document_loaders import Docx2txtLoader

            return Docx2txtLoader(str(file_path))

        if suffix == ".csv":
            from langchain_community.document_loaders import CSVLoader

            return CSVLoader(str(file_path))

        if suffix == ".jsonl":
            return JSONLReviewLoader(file_path)

        if suffix in self.SUPPORTED_TEXT_SUFFIXES:
            return TextLoader(str(file_path), encoding="utf-8")

        raise ValueError(f"Unsupported file type: {suffix}")

    def source_type_for(self, path: str | Path) -> str:
        suffix = Path(path).suffix.lower()

        if suffix == ".pdf":
            return "pdf"
        if suffix == ".docx":
            return "docx"
        if suffix == ".csv":
            return "csv"
        if suffix == ".md":
            return "markdown"
        if suffix == ".jsonl":
            return "jsonl"
        if suffix in self.SUPPORTED_TEXT_SUFFIXES:
            return "text"

        raise ValueError(f"Unsupported file type: {suffix}")


class JSONLReviewLoader:
    """
    Load JSONL records as Documents.

    This loader is intentionally simple and local to the project so large review
    datasets can keep useful structured metadata instead of being treated as one
    huge text file.
    """

    def __init__(self, path: str | Path, encoding: str = "utf-8") -> None:
        self.path = Path(path)
        self.encoding = encoding

    def load(self) -> list[Document]:
        documents: list[Document] = []

        for line_number, line in enumerate(self.path.open("r", encoding=self.encoding), start=1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                documents.append(
                    Document(
                        page_content=line,
                        metadata={
                            "source": str(self.path),
                            "line_number": line_number,
                            "source_type": "jsonl",
                            "parse_error": True,
                        },
                    )
                )
                continue

            documents.append(
                Document(
                    page_content=self._content_from_item(item),
                    metadata=self._metadata_from_item(item, line_number),
                )
            )

        return documents

    def lazy_load(self):
        for line_number, line in enumerate(self.path.open("r", encoding=self.encoding), start=1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                yield Document(
                    page_content=line,
                    metadata={
                        "source": str(self.path),
                        "line_number": line_number,
                        "source_type": "jsonl",
                        "parse_error": True,
                    },
                )
                continue

            yield Document(
                page_content=self._content_from_item(item),
                metadata=self._metadata_from_item(item, line_number),
            )

    def _content_from_item(self, item: dict[str, Any]) -> str:
        title = str(item.get("title") or "").strip()
        text = str(item.get("text") or "").strip()
        rating = item.get("rating")
        asin = item.get("asin")
        verified = item.get("verified_purchase")

        parts = [
            f"Title: {title}" if title else "",
            f"Rating: {rating}" if rating is not None else "",
            f"ASIN: {asin}" if asin else "",
            f"Verified purchase: {verified}" if verified is not None else "",
            f"Review: {text}" if text else "",
        ]

        return "\n".join(part for part in parts if part)

    def _metadata_from_item(self, item: dict[str, Any], line_number: int) -> dict[str, Any]:
        metadata_keys = [
            "rating",
            "title",
            "asin",
            "parent_asin",
            "user_id",
            "timestamp",
            "helpful_vote",
            "verified_purchase",
        ]
        metadata = {
            key: item.get(key)
            for key in metadata_keys
            if item.get(key) is not None
        }
        metadata.update(
            {
                "source": str(self.path),
                "source_name": self.path.name,
                "source_type": "jsonl",
                "line_number": line_number,
            }
        )
        return metadata
