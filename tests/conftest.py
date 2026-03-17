"""Shared test fixtures for oh-hi-markdown."""

import pytest

from oh_hi_markdown.provider import FetchResult


@pytest.fixture
def sample_fetch_result():
    """FetchResult with title, author, date, description, and 3 image refs (PNG, JPG, SVG).

    Used by: T-01, T-02 (no-images variant), T-13, T-14 (overrides title to None), T-25.
    """
    return FetchResult(
        markdown=(
            "# Test Article\n\nSome content.\n\n"
            "![Test image](https://example.com/image1.png)\n\n"
            "![Another image](https://example.com/image2.jpg)\n\n"
            "![Diagram](https://example.com/diagram.svg)\n"
        ),
        title="Test Article Title",
        author="Jane Doe",
        date="2026-01-15T10:00:00Z",
        description="A test article description",
        source_url="https://example.com/test-article",
    )


@pytest.fixture
def jina_success_response():
    """JSON dict matching Jina's Accept: application/json response format.

    Used by: provider and pipeline tests.
    """
    return {
        "code": 200,
        "status": 20000,
        "data": {
            "title": "Test Article Title",
            "description": "A test article description",
            "url": "https://example.com/test-article",
            "content": "# Test Article\n\nSome content.\n\n"
            "![Test image](https://example.com/image1.png)\n\n"
            "![Another image](https://example.com/image2.jpg)\n\n"
            "![Diagram](https://example.com/diagram.svg)\n",
            "publishedTime": "2026-01-15T10:00:00Z",
            "metadata": {
                "author": "Jane Doe",
                "article:author": "Jane Doe",
                "og:author": "J. Doe",
                "article:published_time": "2026-01-15",
            },
            "usage": {"tokens": 42},
        },
    }


@pytest.fixture
def png_bytes():
    """Minimal valid 1x1 PNG image."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def jpg_bytes():
    """Minimal valid JPEG image."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


@pytest.fixture
def svg_bytes():
    """Minimal valid SVG image."""
    return b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
