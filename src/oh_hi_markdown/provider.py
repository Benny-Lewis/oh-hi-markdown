"""Content provider protocol and FetchResult dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class FetchResult:
    """Structured result from a content provider fetch."""

    markdown: str
    title: str | None
    author: str | None
    date: str | None
    description: str | None
    source_url: str


class ContentProvider(Protocol):
    """Protocol for fetching article content from a URL."""

    def fetch(self, url: str) -> FetchResult: ...
