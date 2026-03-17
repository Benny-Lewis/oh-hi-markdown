"""Image download, dedup, and Content-Type validation tests."""

import responses

from oh_hi_markdown.images import download_all
from oh_hi_markdown.parser import ImageRef


@responses.activate
def test_t03_duplicate_image_url(tmp_path, png_bytes):
    """T-03: Duplicate image URL used twice in markdown: downloaded once,
    both references point to same local file."""
    url = "https://example.com/photo.png"
    refs = [
        ImageRef(alt="First", url=url, original_match=f"![First]({url})"),
        ImageRef(alt="Second", url=url, original_match=f"![Second]({url})"),
    ]

    responses.add(
        responses.GET,
        url,
        body=png_bytes,
        status=200,
        content_type="image/png",
    )

    result = download_all(refs, "https://example.com/article", tmp_path)

    # Only one HTTP request should have been made.
    assert len(responses.calls) == 1

    # The URL maps to exactly one ImageDownload.
    assert url in result
    assert result[url].filename == "001-photo.png"


@responses.activate
def test_t04_no_file_extension(tmp_path, png_bytes):
    """T-04: Image URL with no file extension: extension derived from
    Content-Type header."""
    url = "https://cdn.example.com/abc123"
    refs = [ImageRef(alt="img", url=url, original_match=f"![img]({url})")]

    responses.add(
        responses.GET,
        url,
        body=png_bytes,
        status=200,
        content_type="image/png",
    )

    result = download_all(refs, "https://example.com/article", tmp_path)

    assert url in result
    assert result[url].filename == "001-abc123.png"

    # Verify file was actually written.
    images_dir = tmp_path / "images"
    assert (images_dir / "001-abc123.png").exists()


@responses.activate
def test_t05_query_parameters(tmp_path, jpg_bytes):
    """T-05: Image URL with query parameters: parameters stripped from
    filename, image downloaded correctly."""
    url = "https://example.com/photo.jpg?w=800&q=85"
    refs = [ImageRef(alt="photo", url=url, original_match=f"![photo]({url})")]

    responses.add(
        responses.GET,
        url,
        body=jpg_bytes,
        status=200,
        content_type="image/jpeg",
    )

    result = download_all(refs, "https://example.com/article", tmp_path)

    assert url in result
    assert result[url].filename == "001-photo.jpg"

    # Verify file was actually written.
    images_dir = tmp_path / "images"
    assert (images_dir / "001-photo.jpg").exists()


@responses.activate
def test_t15_filename_collision(tmp_path, png_bytes):
    """T-15: Two images resolve to the same sanitized filename:
    disambiguated with suffix (-a, -b)."""
    url1 = "https://example.com/photo.png"
    url2 = "https://cdn.example.com/photo.png"
    refs = [
        ImageRef(alt="one", url=url1, original_match=f"![one]({url1})"),
        ImageRef(alt="two", url=url2, original_match=f"![two]({url2})"),
    ]

    responses.add(responses.GET, url1, body=png_bytes, status=200, content_type="image/png")
    responses.add(responses.GET, url2, body=png_bytes, status=200, content_type="image/png")

    result = download_all(refs, "https://example.com/article", tmp_path)

    assert url1 in result
    assert url2 in result

    # First gets the plain name; second gets the -a suffix.
    assert result[url1].filename == "001-photo.png"
    assert result[url2].filename == "002-photo-a.png"

    # Both files exist on disk.
    images_dir = tmp_path / "images"
    assert (images_dir / "001-photo.png").exists()
    assert (images_dir / "002-photo-a.png").exists()


@responses.activate
def test_t19_non_image_content_type(tmp_path):
    """T-19: Non-image response masquerading as image: image URL returns
    text/html. No file written, markdown URL unchanged, counted as failed."""
    url = "https://example.com/image.jpg"
    refs = [ImageRef(alt="img", url=url, original_match=f"![img]({url})")]

    responses.add(
        responses.GET,
        url,
        body=b"<html>Not an image</html>",
        status=200,
        content_type="text/html",
    )

    result = download_all(refs, "https://example.com/article", tmp_path)

    # URL should NOT be in the result (rejected).
    assert url not in result

    # No files should have been written — images/ dir should not exist.
    images_dir = tmp_path / "images"
    assert not images_dir.exists()


@responses.activate
def test_t26_missing_content_type(tmp_path, jpg_bytes):
    """T-26: Missing Content-Type header with known image extension in URL:
    image accepted and saved. Missing Content-Type with no recognizable
    extension: treated as failed."""
    # Case (a): URL with .jpg extension, no Content-Type → accepted.
    url_with_ext = "https://example.com/photo.jpg"
    # Case (b): URL with no extension, no Content-Type → rejected.
    url_no_ext = "https://example.com/abc123"

    refs = [
        ImageRef(
            alt="a",
            url=url_with_ext,
            original_match=f"![a]({url_with_ext})",
        ),
        ImageRef(
            alt="b",
            url=url_no_ext,
            original_match=f"![b]({url_no_ext})",
        ),
    ]

    # Response with no Content-Type header (pass headers={} explicitly).
    responses.add(
        responses.GET,
        url_with_ext,
        body=jpg_bytes,
        status=200,
        headers={},
        content_type=None,
    )
    responses.add(
        responses.GET,
        url_no_ext,
        body=b"\x00\x01\x02\x03",
        status=200,
        headers={},
        content_type=None,
    )

    result = download_all(refs, "https://example.com/article", tmp_path)

    # (a) accepted — URL with known extension.
    assert url_with_ext in result
    assert result[url_with_ext].filename == "001-photo.jpg"

    # (b) rejected — no extension and no Content-Type.
    assert url_no_ext not in result

    # Only the accepted file should exist.
    images_dir = tmp_path / "images"
    assert (images_dir / "001-photo.jpg").exists()
    image_files = list(images_dir.iterdir())
    assert len(image_files) == 1
