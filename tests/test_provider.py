"""Provider / Jina API error handling tests."""

import pytest
import requests
import responses

from oh_hi_markdown.config import VERSION
from oh_hi_markdown.exceptions import (
    ProviderEmptyContentError,
    ProviderHTTPError,
    ProviderRateLimitError,
    ProviderUnreachableError,
)
from oh_hi_markdown.jina import JinaProvider

TEST_URL = "https://example.com/article"
JINA_URL = f"https://r.jina.ai/{TEST_URL}"


# ── T-11: Jina HTTP 500 ─────────────────────────────────────────────


@responses.activate
def test_t11_jina_http_500():
    """T-11: Jina returns HTTP 500 → ProviderHTTPError(status_code=500).

    Also verifies that:
    - User-Agent header is set correctly.
    - Authorization Bearer header is included when api_key is provided (Gap F-3).
    """
    responses.add(responses.GET, JINA_URL, json={"error": "internal"}, status=500)

    provider = JinaProvider(api_key="test-secret-key")

    with pytest.raises(ProviderHTTPError) as exc_info:
        provider.fetch(TEST_URL)

    assert exc_info.value.status_code == 500

    # Gap F-3: Bearer token is included when api_key is set.
    sent_headers = responses.calls[0].request.headers
    assert sent_headers["Authorization"] == "Bearer test-secret-key"
    assert sent_headers["User-Agent"] == f"ohmd/{VERSION}"


# ── Gap F-4: ConnectionError → ProviderUnreachableError ──────────────


@responses.activate
def test_t11_connection_error_raises_unreachable():
    """Gap F-4: ConnectionError → ProviderUnreachableError (distinct from HTTP 500)."""
    responses.add(
        responses.GET,
        JINA_URL,
        body=requests.ConnectionError("DNS resolution failed"),
    )

    provider = JinaProvider()

    with pytest.raises(ProviderUnreachableError):
        provider.fetch(TEST_URL)


# ── T-12: Jina rate limit 429 ───────────────────────────────────────


@responses.activate
def test_t12_jina_rate_limit_429():
    """T-12: Jina returns HTTP 429 → ProviderRateLimitError.

    Message should suggest setting JINA_API_KEY.
    """
    responses.add(responses.GET, JINA_URL, json={"error": "rate limited"}, status=429)

    provider = JinaProvider()

    with pytest.raises(ProviderRateLimitError, match="JINA_API_KEY"):
        provider.fetch(TEST_URL)


# ── T-27: Jina 200 with empty content ───────────────────────────────


@responses.activate
def test_t27_jina_empty_content():
    """T-27: Jina returns HTTP 200 but with empty/whitespace markdown
    → ProviderEmptyContentError."""
    responses.add(
        responses.GET,
        JINA_URL,
        json={
            "code": 200,
            "status": 20000,
            "data": {
                "title": "Some Title",
                "content": "   \n\n  ",
                "url": TEST_URL,
            },
        },
        status=200,
    )

    provider = JinaProvider()

    with pytest.raises(ProviderEmptyContentError):
        provider.fetch(TEST_URL)
