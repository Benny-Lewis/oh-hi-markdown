"""Parser module tests: image extraction edge cases."""

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


def test_t22_parentheses_in_url():
    """T-22: Image URL containing parentheses or syntax that challenges
    the regex parser. Either processed correctly or left completely unmodified."""
    full_url = "https://en.wikipedia.org/wiki/File:Example_(test).jpg"
    markdown = f"![Wiki image]({full_url})"

    refs = extract(markdown)

    # The regex ([^)]+) stops at the first ')' inside the URL, so it either
    # extracts the full URL (if the regex handles balanced parens) or captures
    # a truncated URL.  Either outcome is acceptable for now; what is NOT
    # acceptable is partial mangling of the rendered output.
    if refs:
        # If any ref was extracted, its URL is either the full correct URL or
        # a truncated version.  Record which case we're in.
        extracted_correctly = refs[0].url == full_url
        # Both outcomes are currently valid — we're documenting behaviour here.
        assert extracted_correctly or refs[0].url.startswith("https://"), (
            f"Extracted URL has unexpected scheme: {refs[0].url!r}"
        )

    # No partial mangling guarantee: when rewrite() is called with the FULL
    # url as the key in url_map (simulating a successful download lookup),
    # the output must be either a correctly rewritten reference or the
    # original text completely unchanged.  A partially-replaced string such
    # as "![Wiki image](./images/001-wiki.jpg).jpg)" is a failure.
    url_map = {full_url: "001-wiki.jpg"}
    result = rewrite(markdown, refs, url_map)

    correctly_rewritten = "![Wiki image](./images/001-wiki.jpg)" in result
    original_preserved = markdown in result

    assert correctly_rewritten or original_preserved, (
        f"Partial mangling detected — output is neither a correct rewrite "
        f"nor the original text.\nOriginal: {markdown!r}\nOutput:   {result!r}"
    )
