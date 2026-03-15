"""Markdown image reference extraction and URL rewriting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

IMAGE_PATTERN = re.compile(r"!\[(.*?)\]\(([^)]+)\)", re.DOTALL)


@dataclass
class ImageRef:
    """A single image reference extracted from markdown."""

    alt: str  # the alt text (may be empty, may be multi-line)
    url: str  # the image URL
    original_match: str  # the full matched text


def extract(markdown: str) -> list[ImageRef]:
    """Extract image references from *markdown*, filtering to http/https URLs only.

    Returns a list of :class:`ImageRef` instances in the order they appear.
    """
    refs: list[ImageRef] = []
    for match in IMAGE_PATTERN.finditer(markdown):
        alt = match.group(1)
        url = match.group(2).strip()
        original_match = match.group(0)

        # Filter to http/https URLs only.
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            refs.append(ImageRef(alt=alt, url=url, original_match=original_match))

    return refs


def rewrite(
    markdown: str,
    image_refs: list[ImageRef],
    url_map: dict[str, str],
) -> str:
    """Rewrite image URLs in *markdown* using *url_map*.

    For each :class:`ImageRef` whose URL is in *url_map*, replace the
    ``original_match`` text with ``![alt](./images/{local_filename})``.

    Args:
        markdown: The original markdown text.
        image_refs: Image references previously extracted by :func:`extract`.
        url_map: Mapping from original URL to local filename (e.g. ``"001-img.png"``).

    Returns:
        The markdown text with image URLs rewritten.
    """
    for ref in image_refs:
        local_filename = url_map.get(ref.url)
        if local_filename is not None:
            new_ref = f"![{ref.alt}](./images/{local_filename})"
            markdown = markdown.replace(ref.original_match, new_ref)
    return markdown
