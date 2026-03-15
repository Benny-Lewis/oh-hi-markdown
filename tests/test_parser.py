"""Parser module tests: image extraction edge cases."""

import pytest

from oh_hi_markdown.parser import extract, rewrite


def test_t16_data_uri_ignored():
    """T-16: Image with data: URI in markdown: left unmodified,
    not downloaded, not counted in summary."""
    data_uri = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAY"
        "AAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhg"
        "GAWjR9awAAAABJRU5ErkJggg=="
    )
    markdown = (
        f"# Article\n\n![inline img]({data_uri})\n\n![remote](https://example.com/photo.png)\n"
    )

    refs = extract(markdown)

    # Only the https URL should be extracted; data URI is excluded.
    assert len(refs) == 1
    assert refs[0].url == "https://example.com/photo.png"

    # The data URI should NOT appear in any extracted ref.
    for ref in refs:
        assert not ref.url.startswith("data:")


def test_t17_empty_alt_text():
    """T-17: Markdown with empty alt text ![](url): image downloaded,
    empty alt preserved in output."""
    markdown = "Some text.\n\n![](https://example.com/img.png)\n\nMore text.\n"

    # Extract should find the image with empty alt text.
    refs = extract(markdown)
    assert len(refs) == 1
    assert refs[0].alt == ""
    assert refs[0].url == "https://example.com/img.png"
    assert refs[0].original_match == "![](https://example.com/img.png)"

    # Rewrite should preserve the empty alt text.
    url_map = {"https://example.com/img.png": "001-img.png"}
    result = rewrite(markdown, refs, url_map)
    assert "![](./images/001-img.png)" in result

    # Original URL should not remain.
    assert "https://example.com/img.png" not in result


@pytest.mark.skip(reason="Not yet implemented — slice 13")
def test_t22_parentheses_in_url():
    """T-22: Image URL containing parentheses or syntax that challenges
    the regex parser. Either processed correctly or left completely unmodified."""
