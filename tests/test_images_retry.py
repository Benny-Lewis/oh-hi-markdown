"""Image retry, failure, and redirect limit tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 7")
def test_t06_image_http_404_with_retry():
    """T-06: Image that returns HTTP 404: retried 3 times, skipped,
    original URL preserved in markdown, run reports 'Partial success' (exit 0).
    The failed image's number slot is consumed."""


@pytest.mark.skip(reason="Not yet implemented — slice 7")
def test_t07_all_images_fail():
    """T-07: All images fail: article.md still created with original URLs,
    images/ folder not created, run reports 'Partial success' (exit 0)."""


@pytest.mark.skip(reason="Not yet implemented — slice 7")
def test_t23_redirect_hop_limit():
    """T-23: Image request exceeds redirect-hop limit (5 hops). Treated as
    failed, original URL preserved, logged correctly."""
