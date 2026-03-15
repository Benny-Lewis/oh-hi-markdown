"""Writer module tests: slug generation, title fallback, front matter."""

import re

from oh_hi_markdown.config import VERSION
from oh_hi_markdown.provider import FetchResult
from oh_hi_markdown.writer import generate_front_matter, generate_slug


def test_t13_title_with_special_characters():
    """T-13: Article title with special characters: slug is properly sanitized,
    folder created with correct name."""
    fr = FetchResult(
        markdown="# My Article\n\nContent here.",
        title="My Article! (2026)",
        author="Jane Doe",
        date="2026-01-15",
        description="A description",
        source_url="https://example.com/article",
    )
    slug, title = generate_slug(fr)
    assert slug == "my-article-2026"
    assert title == "My Article! (2026)"

    # Front matter should use the original (unsanitized) title
    fm = generate_front_matter(fr, "2026-03-15T10:00:00Z")
    assert 'title: "My Article! (2026)"' in fm


def test_t14_title_empty_or_missing():
    """T-14: Article title is empty or missing: fallback naming applied
    per metadata fallback rules."""
    # ── Fallback 3: No title, H1 present → slug from H1 ──
    fr_h1 = FetchResult(
        markdown="# Heading From Markdown\n\nBody text.",
        title=None,
        author=None,
        date=None,
        description=None,
        source_url="https://example.com/article",
    )
    slug, title = generate_slug(fr_h1)
    assert slug == "heading-from-markdown"
    assert title == "Heading From Markdown"

    # ── Fallback 4: No title, no H1, URL has path → slug from URL path ──
    fr_url = FetchResult(
        markdown="Some content without headings.",
        title=None,
        author=None,
        date=None,
        description=None,
        source_url="https://example.com/some-article",
    )
    slug, title = generate_slug(fr_url)
    assert slug == "some-article"
    assert title == "example.com/some-article"

    # ── Fallback 5: No title, no H1, root URL → timestamp fallback ──
    fr_empty = FetchResult(
        markdown="Content with no headings.",
        title=None,
        author=None,
        date=None,
        description=None,
        source_url="https://example.com/",
    )
    slug, title = generate_slug(fr_empty)
    assert re.match(r"^article-\d{8}-\d{6}$", slug)
    assert title == "https://example.com/"


def test_t25_front_matter_field_order_and_omission():
    """T-25: Front matter field order and omission: optional fields missing
    from Jina response are omitted (not blank), required fields present,
    field order matches spec."""
    # author=None and description=None should be omitted entirely
    fr = FetchResult(
        markdown="# Article\n\nContent.",
        title="Test Title",
        author=None,
        date="Wed, 11 Mar 2026 19:06:45 GMT",
        description=None,
        source_url="https://example.com/article",
    )
    fm = generate_front_matter(fr, "2026-03-15T10:00:00Z")

    # Verify required fields are present
    assert 'title: "Test Title"' in fm
    assert 'source_url: "https://example.com/article"' in fm
    assert 'downloaded: "2026-03-15T10:00:00Z"' in fm
    assert f'tool: "ohmd v{VERSION}"' in fm

    # Verify date normalization: "Wed, 11 Mar 2026 19:06:45 GMT" → "2026-03-11"
    assert 'date: "2026-03-11"' in fm

    # Verify optional fields with None value are omitted (not blank)
    assert "author" not in fm
    assert "description" not in fm

    # Verify field order: title < date < source_url < downloaded < tool
    lines = fm.strip().split("\n")
    # Strip the --- delimiters
    field_lines = [line for line in lines if not line.startswith("---")]
    field_names = [line.split(":")[0] for line in field_lines]
    assert field_names == ["title", "date", "source_url", "downloaded", "tool"]
