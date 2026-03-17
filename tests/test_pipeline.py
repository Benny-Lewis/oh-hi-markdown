"""Pipeline end-to-end tests (mocked HTTP)."""

import responses

from oh_hi_markdown.jina import JinaProvider
from oh_hi_markdown.pipeline import run

TEST_URL = "https://example.com/test-article"
JINA_URL = f"https://r.jina.ai/{TEST_URL}"


def _extract_front_matter_keys(text: str) -> list[str]:
    """Extract field keys from YAML front matter in order."""
    keys = []
    in_fm = False
    for line in text.split("\n"):
        if line == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and ": " in line:
            keys.append(line.split(":")[0])
    return keys


@responses.activate
def test_t01_standard_article_with_images(
    tmp_path,
    jina_success_response,
    png_bytes,
    jpg_bytes,
    svg_bytes,
):
    """T-01: Standard article with 3 images: all download successfully,
    all links rewritten to local paths, front matter complete with correct field order."""
    # Mock Jina response.
    responses.add(responses.GET, JINA_URL, json=jina_success_response, status=200)

    # Mock image downloads.
    responses.add(
        responses.GET,
        "https://example.com/image1.png",
        body=png_bytes,
        status=200,
        content_type="image/png",
    )
    responses.add(
        responses.GET,
        "https://example.com/image2.jpg",
        body=jpg_bytes,
        status=200,
        content_type="image/jpeg",
    )
    responses.add(
        responses.GET,
        "https://example.com/diagram.svg",
        body=svg_bytes,
        status=200,
        content_type="image/svg+xml",
    )

    provider = JinaProvider()
    result = run(
        url=TEST_URL,
        output_dir=tmp_path,
        force=False,
        provider=provider,
    )

    # RunResult assertions.
    assert result.outcome == "Success"
    assert result.images_found == 3
    assert result.images_downloaded == 3
    assert result.images_failed == 0

    # Output folder exists.
    output_path = result.output_path
    assert output_path.exists()
    assert output_path.is_dir()

    # article.md exists and has front matter.
    article_path = output_path / "article.md"
    assert article_path.exists()
    article_text = article_path.read_text(encoding="utf-8")

    # Front matter field ordering — per DESIGN.md section 5.
    assert article_text.startswith("---\n")
    expected_keys = ["title", "author", "date", "source_url", "description", "downloaded", "tool"]
    assert _extract_front_matter_keys(article_text) == expected_keys

    # Verify specific field values.
    assert 'title: "Test Article Title"' in article_text
    assert 'author: "Jane Doe"' in article_text
    assert 'date: "2026-01-15"' in article_text
    assert f'source_url: "{TEST_URL}"' in article_text
    assert 'description: "A test article description"' in article_text

    # Links rewritten to local paths.
    assert "![Test image](./images/001-image1.png)" in article_text
    assert "![Another image](./images/002-image2.jpg)" in article_text
    assert "![Diagram](./images/003-diagram.svg)" in article_text

    # Original URLs should NOT appear in the markdown body (after front matter).
    # (source_url is in front matter, which is fine.)
    body_start = article_text.index("---\n", 4) + 4  # after second ---
    body = article_text[body_start:]
    assert "https://example.com/image1.png" not in body
    assert "https://example.com/image2.jpg" not in body
    assert "https://example.com/diagram.svg" not in body

    # images/ subfolder created with all 3 files.
    images_dir = output_path / "images"
    assert images_dir.exists()
    assert images_dir.is_dir()

    image_files = sorted(f.name for f in images_dir.iterdir())
    assert image_files == ["001-image1.png", "002-image2.jpg", "003-diagram.svg"]

    # SVG saved as .svg (D-12).
    svg_file = images_dir / "003-diagram.svg"
    assert svg_file.exists()
    assert svg_file.read_bytes() == svg_bytes

    # Verify Referer header was set on image requests (D-9).
    for call in responses.calls[1:]:  # skip the Jina call
        assert call.request.headers.get("Referer") == TEST_URL

    # Verify image timeout was set correctly (D-9).
    # (responses doesn't expose timeout directly, but we verify the header
    # and trust our implementation sets the timeout from config.)

    # ohmd.log exists.
    log_path = output_path / "ohmd.log"
    assert log_path.exists()

    # .ohmd-marker persists after publish.
    marker = output_path / ".ohmd-marker"
    assert marker.exists()


@responses.activate
def test_t02_article_with_no_images(tmp_path):
    """T-02: Article with no images: article.md created, no images/ folder,
    run reports 'Success.'"""
    # Mock Jina response with NO images in the markdown content.
    jina_response = {
        "code": 200,
        "status": 20000,
        "data": {
            "title": "Test Article Title",
            "description": "A test article description",
            "url": TEST_URL,
            "content": "# Test Article\n\nSome content with no images.\n",
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
    responses.add(responses.GET, JINA_URL, json=jina_response, status=200)

    provider = JinaProvider()
    result = run(
        url=TEST_URL,
        output_dir=tmp_path,
        force=False,
        provider=provider,
    )

    # RunResult assertions
    assert result.outcome == "Success"
    assert result.images_found == 0
    assert result.images_downloaded == 0
    assert result.images_failed == 0

    # Output folder exists at the slug-derived path
    output_path = result.output_path
    assert output_path.exists()
    assert output_path.is_dir()

    # article.md exists and has front matter
    article_path = output_path / "article.md"
    assert article_path.exists()
    article_text = article_path.read_text(encoding="utf-8")

    # Front matter field ordering — per DESIGN.md section 5.
    assert article_text.startswith("---\n")
    expected_keys = ["title", "author", "date", "source_url", "description", "downloaded", "tool"]
    assert _extract_front_matter_keys(article_text) == expected_keys

    # Verify specific field values
    assert 'title: "Test Article Title"' in article_text
    assert 'author: "Jane Doe"' in article_text
    assert 'date: "2026-01-15"' in article_text
    assert f'source_url: "{TEST_URL}"' in article_text
    assert 'description: "A test article description"' in article_text

    # Markdown content is present after front matter
    assert "# Test Article" in article_text
    assert "Some content with no images." in article_text

    # No images/ subfolder
    images_dir = output_path / "images"
    assert not images_dir.exists()

    # ohmd.log exists
    log_path = output_path / "ohmd.log"
    assert log_path.exists()

    # .ohmd-marker persists after publish (moved from temp dir along with everything else)
    marker = output_path / ".ohmd-marker"
    assert marker.exists()
