"""Pipeline end-to-end tests (mocked HTTP)."""

import pytest
import responses

from oh_hi_markdown.jina import JinaProvider
from oh_hi_markdown.pipeline import run

TEST_URL = "https://example.com/test-article"
JINA_URL = f"https://r.jina.ai/{TEST_URL}"


@pytest.mark.skip(reason="Not yet implemented — slice 5")
def test_t01_standard_article_with_images():
    """T-01: Standard article with 3 images: all download successfully,
    all links rewritten to local paths, front matter complete with correct field order."""


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

    # Front matter field ordering: title, author, date, source_url, description,
    # downloaded, tool — per DESIGN.md section 5.
    assert article_text.startswith("---\n")
    lines = article_text.split("\n")
    # Find field keys in order.
    field_keys = []
    in_front_matter = False
    for line in lines:
        if line == "---":
            if in_front_matter:
                break
            in_front_matter = True
            continue
        if in_front_matter and ": " in line:
            key = line.split(":")[0]
            field_keys.append(key)

    expected_keys = ["title", "author", "date", "source_url", "description", "downloaded", "tool"]
    assert field_keys == expected_keys

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

    # No .ohmd-marker file (was in the temp dir, now this is the published output)
    marker = output_path / ".ohmd-marker"
    assert marker.exists()  # marker was created in temp dir and published along with it
