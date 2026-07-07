from __future__ import annotations

from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
import tempfile
from typing import ClassVar


@dataclass(frozen=True)
class ArtifactRecord:
    source: str
    name: str
    path: Path
    media_type: str


class ArtifactService:
    SUPPORTED_SOURCES: ClassVar[set[str]] = {"browser"}
    DEFAULT_MEDIA_TYPE: ClassVar[str] = "application/octet-stream"

    def __init__(
        self,
        *,
        browser_root: Path | None = None,
    ) -> None:
        self.browser_root = (
            browser_root
            or Path(tempfile.gettempdir()) / "ai-assistant-browser-artifacts"
        )

    def public_url(self, artifact_reference: str | None) -> str | None:
        parsed = self.parse_reference(artifact_reference)
        if parsed is None:
            return None

        source, name = parsed
        return f"/internal/ai/artifacts/{source}/{name}"

    def get(self, source: str, name: str) -> ArtifactRecord | None:
        if source not in self.SUPPORTED_SOURCES:
            return None
        if not self._is_safe_name(name):
            return None

        if source == "browser":
            path = self._resolve_browser_artifact(name)
        else:
            path = None

        if path is None or not path.is_file():
            return None

        return ArtifactRecord(
            source=source,
            name=name,
            path=path,
            media_type=self._media_type(path),
        )

    def parse_reference(
        self,
        artifact_reference: str | None,
    ) -> tuple[str, str] | None:
        if not artifact_reference:
            return None

        prefix = "artifact://"
        if not artifact_reference.startswith(prefix):
            return None

        remainder = artifact_reference.removeprefix(prefix)
        source, separator, name = remainder.partition("/")
        if not separator:
            return None
        if source not in self.SUPPORTED_SOURCES:
            return None
        if not self._is_safe_name(name):
            return None

        return source, name

    def _is_safe_name(self, name: str) -> bool:
        return bool(name) and Path(name).name == name

    def _resolve_browser_artifact(self, name: str) -> Path | None:
        if not self._is_safe_name(name):
            return None

        root = self.browser_root.resolve()
        candidate = (root / name).resolve()
        if candidate.parent != root:
            return None
        return candidate

    def _media_type(self, path: Path) -> str:
        media_type, _ = guess_type(path.name)
        return media_type or self.DEFAULT_MEDIA_TYPE
