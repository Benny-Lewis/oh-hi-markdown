"""Jina Reader API implementation of ContentProvider."""

from __future__ import annotations

import logging
import os
import time

import requests

from oh_hi_markdown.config import (
    JINA_API_KEY_ENV,
    JINA_CONNECT_TIMEOUT,
    JINA_READ_TIMEOUT,
    VERSION,
)
from oh_hi_markdown.exceptions import (
    ProviderDecodeError,
    ProviderEmptyContentError,
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderUnreachableError,
)
from oh_hi_markdown.provider import FetchResult

logger = logging.getLogger("ohmd")

# Author metadata keys in priority order.
_AUTHOR_KEYS = ("author", "article:author", "og:author", "citation_author")

# Date metadata fallback keys (after publishedTime).
_DATE_KEYS = ("article:published_time", "date", "DC.date")


class JinaProvider:
    """Fetch article content via the Jina Reader API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get(JINA_API_KEY_ENV)

    def fetch(self, url: str) -> FetchResult:
        """Fetch *url* through Jina Reader and return a FetchResult.

        Raises one of five provider exceptions on failure.
        """
        jina_url = f"https://r.jina.ai/{url}"

        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": f"ohmd/{VERSION}",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-With-Generated-Alt"] = "true"

        auth_status = "Bearer ***" if self._api_key else "none"
        logger.debug("Jina request: GET %s (Authorization: %s)", jina_url, auth_status)

        start_time = time.monotonic()
        try:
            resp = requests.get(
                jina_url,
                headers=headers,
                timeout=(JINA_CONNECT_TIMEOUT, JINA_READ_TIMEOUT),
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            elapsed = time.monotonic() - start_time
            logger.debug("Jina request failed after %.2fs: %s", elapsed, exc)
            raise ProviderUnreachableError(str(exc)) from exc

        elapsed = time.monotonic() - start_time
        logger.debug(
            "Jina response: HTTP %d, %.2fs, %d bytes",
            resp.status_code,
            elapsed,
            len(resp.content),
        )

        # --- HTTP error mapping ---
        if resp.status_code == 429:
            msg = f"Jina rate limit exceeded (HTTP 429). Set {JINA_API_KEY_ENV} for a higher quota."
            raise ProviderRateLimitError(msg)

        if resp.status_code >= 400:
            raise ProviderHTTPError(resp.status_code)

        # --- Decode JSON ---
        try:
            body = resp.json()
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProviderDecodeError(str(exc)) from exc

        data: dict = body.get("data", {})
        content: str = data.get("content", "")

        if not content or not content.strip():
            raise ProviderEmptyContentError(
                "Jina returned HTTP 200 but the markdown content is empty."
            )

        # --- Metadata extraction ---
        metadata: dict = data.get("metadata", {})

        author = self._first_nonempty(metadata, _AUTHOR_KEYS)
        date = data.get("publishedTime") or self._first_nonempty(metadata, _DATE_KEYS)

        return FetchResult(
            markdown=content,
            title=data.get("title") or None,
            author=author,
            date=date,
            description=data.get("description") or None,
            source_url=url,
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _first_nonempty(mapping: dict, keys: tuple[str, ...]) -> str | None:
        """Return the first non-empty string value for *keys*, or None."""
        for key in keys:
            value = mapping.get(key)
            if value and isinstance(value, str) and value.strip():
                return value.strip()
        return None
