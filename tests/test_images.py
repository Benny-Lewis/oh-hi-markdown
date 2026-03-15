"""Image download, dedup, and Content-Type validation tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t03_duplicate_image_url():
    """T-03: Duplicate image URL used twice in markdown: downloaded once,
    both references point to same local file."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t04_no_file_extension():
    """T-04: Image URL with no file extension: extension derived from
    Content-Type header."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t05_query_parameters():
    """T-05: Image URL with query parameters: parameters stripped from
    filename, image downloaded correctly."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t15_filename_collision():
    """T-15: Two images resolve to the same sanitized filename:
    disambiguated with suffix (-a, -b)."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t19_non_image_content_type():
    """T-19: Non-image response masquerading as image: image URL returns
    text/html. No file written, markdown URL unchanged, counted as failed."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t26_missing_content_type():
    """T-26: Missing Content-Type header with known image extension in URL:
    image accepted and saved. Missing Content-Type with no recognizable
    extension: treated as failed."""
