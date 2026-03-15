"""Provider / Jina API error handling tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 2")
def test_t11_jina_http_500():
    """T-11: Jina returns HTTP 500: exit code 2, descriptive error,
    no output folder created."""


@pytest.mark.skip(reason="Not yet implemented — slice 2")
def test_t12_jina_rate_limit_429():
    """T-12: Jina returns HTTP 429 (rate limit): exit code 2,
    message suggests setting JINA_API_KEY."""


@pytest.mark.skip(reason="Not yet implemented — slice 2")
def test_t27_jina_empty_content():
    """T-27: Jina returns HTTP 200 but with empty or whitespace-only markdown:
    exit code 2, descriptive error, no output folder created."""
