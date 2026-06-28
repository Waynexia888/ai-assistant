from typing import Any

from pydantic import BaseModel, Field


class BrowserLink(BaseModel):
    text: str | None = None
    href: str
    visible: bool = True


class BrowserElement(BaseModel):
    role: str | None = None
    name: str | None = None
    text: str | None = None
    selector: str | None = None
    visible: bool = True


class BrowserObservation(BaseModel):
    url: str | None = None
    title: str | None = None
    text: str | None = None
    public_summary: str | None = None
    links: list[BrowserLink] = Field(default_factory=list)
    elements: list[BrowserElement] = Field(default_factory=list)
    screenshot: str | None = None
    error: dict[str, Any] | None = None
    loading: bool = False
    raw: dict[str, Any] | None = None
