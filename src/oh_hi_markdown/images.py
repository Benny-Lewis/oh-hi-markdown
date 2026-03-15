"""Image download, deduplication, retry, and filename resolution."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from oh_hi_markdown.config import IMAGE_CONNECT_TIMEOUT, IMAGE_READ_TIMEOUT, VERSION
from oh_hi_markdown.parser import ImageRef

logger = logging.getLogger("ohmd")

# Content-Type to extension mapping per DESIGN.md section 4.
_CONTENT_TYPE_MAP: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}

# Known image extensions for URL-based fallback (includes .jpeg alias).
_KNOWN_EXTENSIONS: set[str] = set(_CONTENT_TYPE_MAP.values()) | {".jpeg"}


@dataclass
class ImageDownload:
    """Result of a successful single-image download."""

    filename: str  # e.g., "002-diagram.png"
    size: int  # bytes


def _extract_url_filename(url: str) -> str:
    """Extract filename from a URL path (after last /, before ?)."""
    parsed = urlparse(url)
    path = parsed.path
    # Get the last path component.
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    return filename


def _resolve_filename(
    url: str,
    content_type: str | None,
    sequence: int,
) -> str:
    """Resolve the local filename for a downloaded image.

    Implements the 8-step process from DESIGN.md (without collision handling).
    """
    # Step 1: Extract filename from URL path.
    raw_name = _extract_url_filename(url)

    # Step 2: URL-decode the filename.
    raw_name = unquote(raw_name)

    # Step 3: Sanitize — replace non-[a-zA-Z0-9._-] with hyphen.
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "-", raw_name)

    # Split into base name and extension before further processing.
    if "." in sanitized:
        last_dot = sanitized.rfind(".")
        base = sanitized[:last_dot]
        url_ext = sanitized[last_dot:]  # includes the dot
    else:
        base = sanitized
        url_ext = ""

    # Step 4: Collapse consecutive hyphens, strip leading/trailing hyphens from base name.
    base = re.sub(r"-{2,}", "-", base)
    base = base.strip("-")

    # Step 5: If empty, use 'image' as base name.
    if not base:
        base = "image"

    # Step 6: Determine extension — prefer Content-Type mapping, fall back to URL extension.
    ext = ""
    if content_type:
        # Normalize: take only the mime type part (strip parameters like charset).
        mime = content_type.split(";")[0].strip().lower()
        ext = _CONTENT_TYPE_MAP.get(mime, "")

    if not ext:
        # Fall back to URL extension if it's a known image extension.
        url_ext_lower = url_ext.lower()
        if url_ext_lower in _KNOWN_EXTENSIONS:
            ext = url_ext_lower
        elif url_ext:
            # Use the URL extension even if unknown.
            ext = url_ext

    # Step 7: Prepend sequence number — {NNN}-{sanitized-name}.{ext}
    filename = f"{sequence:03d}-{base}{ext}"

    # Step 8: Collision check — skipped for this slice.

    return filename


def download_all(
    image_refs: list[ImageRef],
    article_url: str,
    temp_dir: Path,
) -> dict[str, ImageDownload]:
    """Download all images referenced by *image_refs*.

    Sequential download with deduplication by URL. Creates an ``images/``
    subfolder inside *temp_dir* only if at least one download succeeds.

    Args:
        image_refs: Image references extracted from the markdown.
        article_url: The article URL, used as the Referer header.
        temp_dir: The temporary directory for this pipeline run.

    Returns:
        Dict mapping original URL to :class:`ImageDownload` for successes only.
    """
    result: dict[str, ImageDownload] = {}
    images_dir = temp_dir / "images"
    images_dir_created = False
    sequence = 0

    for ref in image_refs:
        sequence += 1

        # Dedup by URL: if already downloaded, skip but reuse entry.
        if ref.url in result:
            logger.debug("Skipping duplicate URL: %s", ref.url)
            continue

        # Download the image.
        try:
            resp = requests.get(
                ref.url,
                headers={
                    "User-Agent": f"ohmd/{VERSION}",
                    "Referer": article_url,
                },
                timeout=(IMAGE_CONNECT_TIMEOUT, IMAGE_READ_TIMEOUT),
                stream=True,
            )
            resp.raise_for_status()
        except (requests.RequestException, OSError) as exc:
            logger.warning("Failed to download %s: %s", ref.url, exc)
            continue

        content_type = resp.headers.get("Content-Type")
        data = resp.content

        # Resolve filename.
        filename = _resolve_filename(ref.url, content_type, sequence)

        # Create images/ subfolder on first success (S-2).
        if not images_dir_created:
            images_dir.mkdir(parents=True, exist_ok=True)
            images_dir_created = True

        # Write file.
        file_path = images_dir / filename
        file_path.write_bytes(data)

        result[ref.url] = ImageDownload(filename=filename, size=len(data))
        logger.info("Downloaded %s -> %s (%d bytes)", ref.url, filename, len(data))

    return result
