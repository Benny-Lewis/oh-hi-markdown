"""Image retry, failure, and redirect limit tests."""

from unittest.mock import patch

import responses

from oh_hi_markdown.images import download_all
from oh_hi_markdown.jina import JinaProvider
from oh_hi_markdown.parser import ImageRef
from oh_hi_markdown.pipeline import run

TEST_URL = "https://example.com/test-article"
JINA_URL = f"https://r.jina.ai/{TEST_URL}"


@responses.activate
@patch("oh_hi_markdown.images.BACKOFF_DELAYS", (0, 0, 0))
def test_t06_image_http_404_with_retry(tmp_path):
    """T-06: Image that returns HTTP 404: retried 3 times, skipped,
    original URL preserved in markdown, run reports 'Partial success' (exit 0).
    The failed image's number slot is consumed."""
    url = "https://example.com/missing.png"
    refs = [ImageRef(alt="missing", url=url, original_match=f"![missing]({url})")]

    # Return 404 for ALL requests — the image never succeeds.
    responses.add(
        responses.GET,
        url,
        body=b"Not Found",
        status=404,
    )

    result = download_all(refs, "https://example.com/article", tmp_path)

    # 4 total attempts: 1 initial + 3 retries.
    assert len(responses.calls) == 4

    # URL NOT in result (all attempts failed).
    assert url not in result

    # images/ dir should not exist (no successful downloads).
    assert not (tmp_path / "images").exists()


@responses.activate
@patch("oh_hi_markdown.images.BACKOFF_DELAYS", (0, 0, 0))
def test_t07_all_images_fail(tmp_path):
    """T-07: All images fail: article.md still created with original URLs,
    images/ folder not created, run reports 'Partial success' (exit 0)."""
    # Jina returns markdown with one image reference.
    jina_response = {
        "code": 200,
        "status": 20000,
        "data": {
            "title": "Test Article Title",
            "description": "A test article description",
            "url": TEST_URL,
            "content": (
                "# Test Article\n\nSome content.\n\n"
                "![Broken image](https://example.com/broken.png)\n"
            ),
            "publishedTime": "2026-01-15T10:00:00Z",
            "metadata": {
                "author": "Jane Doe",
                "article:author": "Jane Doe",
            },
            "usage": {"tokens": 42},
        },
    }
    responses.add(responses.GET, JINA_URL, json=jina_response, status=200)

    # Image always returns 404.
    responses.add(
        responses.GET,
        "https://example.com/broken.png",
        body=b"Not Found",
        status=404,
    )

    provider = JinaProvider()
    result = run(
        url=TEST_URL,
        output_dir=tmp_path,
        force=False,
        provider=provider,
    )

    # Outcome is "Partial success" because images were found but all failed.
    assert result.outcome == "Partial success"
    assert result.images_found == 1
    assert result.images_downloaded == 0
    assert result.images_failed == 1

    # article.md exists with original URLs (not rewritten).
    article_path = result.output_path / "article.md"
    assert article_path.exists()
    article_text = article_path.read_text(encoding="utf-8")
    assert "![Broken image](https://example.com/broken.png)" in article_text

    # No images/ folder.
    images_dir = result.output_path / "images"
    assert not images_dir.exists()


@responses.activate
@patch("oh_hi_markdown.images.BACKOFF_DELAYS", (0, 0, 0))
def test_t23_redirect_hop_limit(tmp_path):
    """T-23: Image request exceeds redirect-hop limit (5 hops). Treated as
    failed, original URL preserved, logged correctly."""
    import requests as real_requests

    url = "https://example.com/redirect-loop.png"
    refs = [ImageRef(alt="redir", url=url, original_match=f"![redir]({url})")]

    # Patch session.get to raise TooManyRedirects directly, since the
    # `responses` library does not simulate redirect following.
    original_session_get = real_requests.Session.get
    call_count = 0

    def fake_get(self, request_url, **kwargs):
        nonlocal call_count
        if request_url == url:
            call_count += 1
            raise real_requests.TooManyRedirects("Exceeded 5 redirects.")
        return original_session_get(self, request_url, **kwargs)

    with patch.object(real_requests.Session, "get", fake_get):
        result = download_all(refs, "https://example.com/article", tmp_path)

    # TooManyRedirects must NOT be retried — exactly 1 attempt.
    assert call_count == 1

    # URL NOT in result (redirect limit exceeded).
    assert url not in result

    # images/ dir should not exist.
    assert not (tmp_path / "images").exists()
