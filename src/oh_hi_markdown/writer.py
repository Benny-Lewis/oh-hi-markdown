"""Front matter generation, slug creation, and article.md assembly."""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from oh_hi_markdown.config import SLUG_MAX_LENGTH, VERSION
from oh_hi_markdown.provider import FetchResult


def _yaml_escape(value: str) -> str:
    """Escape a string for use as a YAML double-quoted value.

    Handles backslashes first, then double quotes, to avoid double-escaping.
    """
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def _transliterate(text: str) -> str:
    """Transliterate non-ASCII characters to ASCII equivalents.

    Uses NFKD normalization to decompose characters, then strips non-ASCII
    combining marks.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Lowercase, replace spaces/underscores with hyphens, strip non-alphanumeric
    characters (except hyphens), collapse consecutive hyphens, strip
    leading/trailing hyphens, truncate to SLUG_MAX_LENGTH at a word boundary.
    """
    slug = text.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")

    if len(slug) > SLUG_MAX_LENGTH:
        # Truncate at a word boundary (hyphen).
        truncated = slug[:SLUG_MAX_LENGTH]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 0:
            slug = truncated[:last_hyphen]
        else:
            slug = truncated
    return slug


def _extract_h1(markdown: str) -> str | None:
    """Extract the first H1 heading text from markdown content."""
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _url_path_slug(url: str) -> tuple[str, str] | None:
    """Extract a meaningful slug and title from a URL path.

    Returns (slug, title) or None if the path is empty or just '/'.
    The title is 'domain/path' and the slug is derived from the path component.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return None
    slug = _slugify(path)
    if not slug:
        return None
    title = f"{parsed.netloc}/{path}"
    return slug, title


def _normalize_date(date_str: str) -> str:
    """Normalize a date string to ISO 8601 YYYY-MM-DD format.

    Uses python-dateutil for robust parsing. Returns the original string
    if parsing fails.
    """
    try:
        dt = dateutil_parser.parse(date_str)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return date_str


def generate_slug(fetch_result: FetchResult) -> tuple[str, str]:
    """Generate a slug and front-matter title from a FetchResult.

    Implements the 5-priority title fallback chain:
    1. Jina title -> slugify
    2. Jina title -> transliterate then slugify
    3. H1 heading from markdown -> slugify (with transliteration)
    4. URL path -> slugify
    5. Timestamp fallback

    Returns:
        (slug, front_matter_title) tuple.
    """
    # Priority 1: Direct slugification of the Jina title
    if fetch_result.title:
        slug = _slugify(fetch_result.title)
        if slug:
            return slug, fetch_result.title

        # Priority 2: Transliterate then slugify the Jina title
        transliterated = _transliterate(fetch_result.title)
        slug = _slugify(transliterated)
        if slug:
            return slug, fetch_result.title

    # Priority 3: H1 heading from markdown
    h1 = _extract_h1(fetch_result.markdown)
    if h1:
        slug = _slugify(h1)
        if not slug:
            slug = _slugify(_transliterate(h1))
        if slug:
            return slug, h1

    # Priority 4: URL path
    url_result = _url_path_slug(fetch_result.source_url)
    if url_result:
        return url_result

    # Priority 5: Timestamp fallback
    now = datetime.now(timezone.utc)
    slug = f"article-{now.strftime('%Y%m%d-%H%M%S')}"
    return slug, fetch_result.source_url


def generate_front_matter(
    fetch_result: FetchResult,
    downloaded_timestamp: str,
) -> str:
    """Generate YAML front matter block from a FetchResult.

    Fields are in fixed order, optional fields omitted if None.
    All values are double-quoted strings with proper escaping.

    Args:
        fetch_result: The fetch result containing article metadata.
        downloaded_timestamp: ISO 8601 timestamp of when the article was downloaded.

    Returns:
        Front matter string including the --- delimiters.
    """
    slug, title = generate_slug(fetch_result)

    # Normalize date if present
    date = None
    if fetch_result.date:
        date = _normalize_date(fetch_result.date)

    # Build fields in spec order: title, author, date, source_url, description,
    # downloaded, tool
    lines = ["---"]

    # title (required)
    lines.append(f'title: "{_yaml_escape(title)}"')

    # author (optional)
    if fetch_result.author is not None:
        lines.append(f'author: "{_yaml_escape(fetch_result.author)}"')

    # date (optional)
    if date is not None:
        lines.append(f'date: "{_yaml_escape(date)}"')

    # source_url (required)
    lines.append(f'source_url: "{_yaml_escape(fetch_result.source_url)}"')

    # description (optional)
    if fetch_result.description is not None:
        lines.append(f'description: "{_yaml_escape(fetch_result.description)}"')

    # downloaded (required)
    lines.append(f'downloaded: "{_yaml_escape(downloaded_timestamp)}"')

    # tool (required)
    lines.append(f'tool: "ohmd v{VERSION}"')

    lines.append("---")

    return "\n".join(lines) + "\n"


def assemble(fetch_result: FetchResult, markdown: str, temp_dir: str) -> str:
    """Assemble front matter and markdown into article.md.

    Writes the concatenation of front matter + blank line + markdown content
    to article.md in the provided directory.

    Args:
        fetch_result: The fetch result containing article metadata.
        markdown: The markdown content (possibly with rewritten image paths).
        temp_dir: Directory to write article.md into.

    Returns:
        The path to the written article.md file.
    """
    downloaded = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    front_matter = generate_front_matter(fetch_result, downloaded)

    content = front_matter + "\n" + markdown
    path = os.path.join(temp_dir, "article.md")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path
