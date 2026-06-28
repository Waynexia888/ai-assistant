import base64
import binascii
import re
import tempfile
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.domain.models.browser import (
    BrowserElement,
    BrowserLink,
    BrowserObservation,
)
from app.domain.models.tool_result import ToolResult


PAGE_URL_PATTERN = re.compile(r"(?:^|[-*]\s*)Page URL:\s*(\S+)", re.MULTILINE)
PAGE_TITLE_PATTERN = re.compile(r"(?:^|[-*]\s*)Page Title:\s*(.+)$", re.MULTILINE)
ELEMENT_PATTERN = re.compile(
    r'^\s*-\s+(?P<role>[a-zA-Z][\w-]*)'
    r'(?:\s+"(?P<name>[^"]*)")?'
    r'(?:\s+\[ref=(?P<ref>[^\]]+)\])?',
    re.MULTILINE,
)
SNAPSHOT_REFERENCE_PATTERN = re.compile(
    r"\[Snapshot\]\((?P<path>\.playwright-mcp/[^)]+\.ya?ml)\)"
)
SCREENSHOT_REFERENCE_PATTERN = re.compile(
    r"\[Screenshot\]\((?P<path>\.playwright-mcp/[^)]+\.(?:png|jpe?g|webp))\)"
)
PUBLIC_HEADING_PATTERN = re.compile(
    r'^\s*-\s+heading\s+"(?P<text>[^"]+)"',
    re.MULTILINE,
)
PUBLIC_PARAGRAPH_PATTERN = re.compile(
    r"^\s*-\s+paragraph(?:\s+\[[^\]]+\])?:\s*(?P<text>.+)$",
    re.MULTILINE,
)


class BrowserArtifactStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(tempfile.gettempdir()) / "ai-assistant-browser-artifacts"

    def save_image(self, encoded_data: str, mime_type: str | None) -> str | None:
        try:
            image_bytes = base64.b64decode(encoded_data, validate=True)
        except (ValueError, binascii.Error):
            return None

        if not image_bytes:
            return None

        extension = {
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }.get(mime_type or "", "png")
        artifact_name = f"screenshot-{uuid4().hex}.{extension}"
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / artifact_name).write_bytes(image_bytes)
        return f"artifact://browser/{artifact_name}"

    def resolve(self, artifact_reference: str) -> Path | None:
        prefix = "artifact://browser/"
        if not artifact_reference.startswith(prefix):
            return None
        artifact_name = artifact_reference.removeprefix(prefix)
        if not artifact_name or Path(artifact_name).name != artifact_name:
            return None
        return self.root / artifact_name

    def save_file(self, source: Path) -> str | None:
        if not source.is_file():
            return None
        artifact_name = f"screenshot-{uuid4().hex}{source.suffix.lower()}"
        self.root.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, self.root / artifact_name)
        return f"artifact://browser/{artifact_name}"


class BrowserObservationNormalizer:
    def __init__(
        self,
        artifact_store: BrowserArtifactStore | None = None,
        playwright_output_root: Path | None = None,
    ) -> None:
        self.artifact_store = artifact_store or BrowserArtifactStore()
        self.playwright_output_root = (
            playwright_output_root or Path.cwd() / ".playwright-mcp"
        ).resolve()

    def normalize(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        raw_result: Any,
    ) -> ToolResult[dict[str, Any]]:
        payload = self._to_plain_value(raw_result)
        if not isinstance(payload, dict):
            payload = {"content": payload}

        is_error = bool(payload.get("isError", payload.get("is_error", False)))
        text = self._extract_text(payload)
        structured = payload.get(
            "structuredContent",
            payload.get("structured_content"),
        )
        structured = structured if isinstance(structured, dict) else {}

        observation = BrowserObservation(
            url=self._extract_url(structured, text, arguments),
            title=self._extract_title(structured, text),
            text=text or None,
            public_summary=self._build_public_summary(
                title=self._extract_title(structured, text),
                text=text,
            ),
            links=self._extract_links(structured),
            elements=self._extract_elements(structured, text),
            screenshot=self._save_screenshot(payload, text),
            error=(
                {
                    "type": "mcp_tool_error",
                    "tool": tool_name,
                    "message": text or "Browser MCP tool returned an error.",
                }
                if is_error
                else None
            ),
            loading=bool(structured.get("loading", False)),
        )
        content = self._build_content(tool_name, observation)
        return ToolResult(
            success=not is_error,
            message=(observation.error or {}).get("message"),
            data={
                "type": "browser_observation",
                "content": content,
                "summary": self._build_summary(observation),
                "observation": observation.model_dump(mode="json", exclude={"raw"}),
            },
        )

    def error(
        self,
        *,
        server: str,
        tool_name: str,
        arguments: dict[str, Any],
        error: Exception,
    ) -> ToolResult[dict[str, Any]]:
        observation = BrowserObservation(
            url=str(arguments.get("url")) if arguments.get("url") else None,
            error={
                "type": "mcp_tool_error",
                "server": server,
                "tool": tool_name,
                "message": str(error),
                "retryable": False,
            },
        )
        return ToolResult(
            success=False,
            message=str(error),
            data={
                "type": "browser_observation",
                "content": f"Browser observation failed: {error}",
                "summary": "Browser observation failed.",
                "observation": observation.model_dump(mode="json", exclude={"raw"}),
            },
        )

    def _to_plain_value(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json", by_alias=True)
        if isinstance(value, list):
            return [self._to_plain_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_plain_value(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): self._to_plain_value(item)
                for key, item in value.items()
            }
        return value

    def _extract_text(self, payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if isinstance(content, str):
            return content.strip()
        if not isinstance(content, list):
            return ""
        parts = [
            str(item.get("text")).strip()
            for item in content
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text")
        ]
        text = "\n".join(part for part in parts if part)
        snapshot_text = self._read_playwright_reference(
            text,
            SNAPSHOT_REFERENCE_PATTERN,
        )
        if snapshot_text:
            return f"{text}\n\n### Accessibility Snapshot\n{snapshot_text}"
        return text

    def _extract_url(
        self,
        structured: dict[str, Any],
        text: str,
        arguments: dict[str, Any],
    ) -> str | None:
        value = structured.get("url")
        if isinstance(value, str) and value:
            return value
        match = PAGE_URL_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        argument_url = arguments.get("url")
        return str(argument_url) if argument_url else None

    def _extract_title(self, structured: dict[str, Any], text: str) -> str | None:
        value = structured.get("title")
        if isinstance(value, str) and value:
            return value
        match = PAGE_TITLE_PATTERN.search(text)
        return match.group(1).strip() if match else None

    def _extract_links(self, structured: dict[str, Any]) -> list[BrowserLink]:
        links = structured.get("links")
        if not isinstance(links, list):
            return []

        results = []
        for link in links:
            if not isinstance(link, dict) or not link.get("href"):
                continue
            results.append(
                BrowserLink(
                    text=str(link.get("text")) if link.get("text") is not None else None,
                    href=str(link["href"]),
                    visible=bool(link.get("visible", True)),
                )
            )
        return results

    def _extract_elements(
        self,
        structured: dict[str, Any],
        text: str,
    ) -> list[BrowserElement]:
        elements = structured.get("elements")
        if isinstance(elements, list):
            return [
                BrowserElement.model_validate(element)
                for element in elements
                if isinstance(element, dict)
            ]

        return [
            BrowserElement(
                role=match.group("role"),
                name=match.group("name"),
                selector=(
                    f"ref={match.group('ref')}"
                    if match.group("ref")
                    else None
                ),
            )
            for match in ELEMENT_PATTERN.finditer(text)
            if match.group("role").lower() != "page"
        ]

    def _save_screenshot(
        self,
        payload: dict[str, Any],
        text: str,
    ) -> str | None:
        content = payload.get("content")
        if not isinstance(content, list):
            return None
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "image":
                continue
            data = item.get("data")
            if not isinstance(data, str):
                continue
            mime_type = item.get("mimeType", item.get("mime_type"))
            return self.artifact_store.save_image(
                data,
                str(mime_type) if mime_type else None,
            )
        screenshot_path = self._resolve_playwright_reference(
            text,
            SCREENSHOT_REFERENCE_PATTERN,
        )
        if screenshot_path is not None:
            return self.artifact_store.save_file(screenshot_path)
        return None

    def _read_playwright_reference(
        self,
        text: str,
        pattern: re.Pattern[str],
    ) -> str | None:
        path = self._resolve_playwright_reference(text, pattern)
        if path is None:
            return None
        try:
            if path.stat().st_size > 1_000_000:
                return None
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None

    def _resolve_playwright_reference(
        self,
        text: str,
        pattern: re.Pattern[str],
    ) -> Path | None:
        match = pattern.search(text)
        if match is None:
            return None
        relative_path = Path(match.group("path"))
        candidate = (Path.cwd() / relative_path).resolve()
        if candidate.parent != self.playwright_output_root:
            return None
        return candidate if candidate.is_file() else None

    def _build_content(
        self,
        tool_name: str,
        observation: BrowserObservation,
    ) -> str:
        location = observation.url or "the current page"
        title = f" Page title: {observation.title}." if observation.title else ""
        if tool_name == "browser.open":
            return f"Opened {location}.{title}".strip()
        if tool_name == "browser.screenshot":
            return f"Captured a screenshot for {location}.{title}".strip()
        return f"Observed {location}.{title}".strip()

    def _build_summary(self, observation: BrowserObservation) -> str:
        if observation.error:
            return "Browser observation failed."
        if observation.title:
            return f"Observed page: {observation.title}."
        if observation.url:
            return f"Observed page: {observation.url}."
        return "Browser page observed successfully."

    def _build_public_summary(
        self,
        *,
        title: str | None,
        text: str,
        max_characters: int = 6000,
    ) -> str | None:
        headings = self._unique_public_text(
            match.group("text")
            for match in PUBLIC_HEADING_PATTERN.finditer(text)
            if not self._is_public_noise(match.group("text"))
        )
        paragraphs = self._unique_public_text(
            match.group("text")
            for match in PUBLIC_PARAGRAPH_PATTERN.finditer(text)
            if not self._is_cookie_notice(match.group("text"))
            and not match.group("text").lstrip().startswith(("“", '"'))
        )

        sections = []
        if title:
            sections.append(f"Page title: {title}")
        if headings:
            sections.append(
                "Key headings:\n"
                + "\n".join(f"- {heading}" for heading in headings[:16])
            )
        if paragraphs:
            sections.append(
                "Page details:\n"
                + "\n".join(f"- {paragraph}" for paragraph in paragraphs[:16])
            )

        summary = "\n\n".join(sections).strip()
        if not summary:
            return None
        if len(summary) <= max_characters:
            return summary
        return f"{summary[:max_characters]}... [truncated]"

    def _unique_public_text(self, values) -> list[str]:
        seen: set[str] = set()
        results: list[str] = []
        for value in values:
            normalized = " ".join(str(value).split()).strip(" '\"")
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            results.append(normalized)
        return results

    def _is_cookie_notice(self, value: str) -> bool:
        normalized = value.lower()
        markers = [
            "we use cookies",
            "advertising partners",
            "opt out at any time",
            "cookie policy",
        ]
        return any(marker in normalized for marker in markers)

    def _is_public_noise(self, value: str) -> bool:
        normalized = " ".join(value.lower().split())
        if normalized in {
            "we value your privacy",
            "products",
            "resources",
            "company",
            "sign up for our newsletter to stay up to date",
        }:
            return True

        words = normalized.split()
        return len(words) >= 8 and all(len(word) == 1 for word in words)
