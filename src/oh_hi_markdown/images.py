"""Image download, deduplication, retry, and filename resolution."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from oh_hi_markdown.config import (
    BACKOFF_DELAYS,
    IMAGE_CONNECT_TIMEOUT,
    IMAGE_COUNT_WARNING,
    IMAGE_READ_TIMEOUT,
    MAX_IMAGE_RETRIES,
    MAX_REDIRECT_HOPS,
    SINGLE_IMAGE_SIZE_WARNING,
    TOTAL_DOWNLOAD_SIZE_WARNING,
    VERSION,
)
from oh_hi_markdown.exceptions import FilesystemError
from oh_hi_markdown.parser import ImageRef

logger = logging.getLogger("ohmd")


def _is_private_url(url: str) -> bool:
    """Return True if *url* resolves to a private/loopback/link-local address.

    Used to prevent SSRF via image redirect — validates the final URL after
    redirects are followed.
    """
    import ipaddress

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname == "localhost":
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    if hasattr(address, "ipv4_mapped") and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_loopback or address.is_private or address.is_link_local


def _safe_get(
    session: requests.Session,
    url: str,
    *,
    headers: dict[str, str],
    timeout: tuple[int, int],
) -> requests.Response:
    """GET *url* following redirects manually with SSRF validation at each hop.

    Raises ``requests.TooManyRedirects`` if the hop count exceeds
    ``session.max_redirects``.  Raises ``requests.ConnectionError`` if a
    redirect target resolves to a private/internal address.
    """
    current_url = url
    for hop in range(session.max_redirects + 1):
        resp = session.get(
            current_url,
            headers=headers,
            timeout=timeout,
            stream=True,
            allow_redirects=False,
        )
        if resp.is_redirect:
            location = resp.headers.get("Location", "")
            if not location:
                break  # No Location header — treat as final response.
            # Resolve relative redirects.
            if location.startswith("/"):
                parsed = urlparse(current_url)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            if _is_private_url(location):
                raise requests.ConnectionError(
                    f"Redirect to private/internal address blocked: {location}"
                )
            current_url = location
            continue
        return resp
    raise requests.TooManyRedirects(f"Exceeded {session.max_redirects} redirects for {url}")


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


def _extract_url_extension(url: str) -> str:
    """Return the lowercased file extension from *url* (e.g. ``'.jpg'``).

    Returns an empty string when no extension is present.
    """
    filename = _extract_url_filename(url)
    if "." in filename:
        return filename[filename.rfind(".") :].lower()
    return ""


def _resolve_filename(
    url: str,
    content_type: str | None,
    sequence: int,
    assigned: set[str] | None = None,
) -> str:
    """Resolve the local filename for a downloaded image.

    Implements the 8-step process from DESIGN.md.

    Args:
        url: The image URL.
        content_type: The Content-Type header value (may be ``None``).
        sequence: 1-based sequence number for this image.
        assigned: Set of filenames already assigned in this run.
            Used for collision disambiguation (step 8).  The resolved
            name is added to this set before returning.
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
        elif content_type and content_type.split(";")[0].strip().lower().startswith("image/"):
            # Unknown image/* subtype with no URL extension → use .bin
            ext = ".bin"

    # Step 7: Prepend sequence number — {NNN}-{sanitized-name}.{ext}
    filename = f"{sequence:03d}-{base}{ext}"

    # Step 8: Collision disambiguation.
    # Track collisions by base name + extension (the part without the sequence
    # prefix), since the sequence prefix alone prevents identical full names.
    if assigned is not None:
        base_key = f"{base}{ext}"
        if base_key in assigned:
            # Try suffixes -a, -b, -c, ... -z, then -aa, -ab, ...
            resolved = False
            for suffix_ord in range(ord("a"), ord("z") + 1):
                candidate_key = f"{base}-{chr(suffix_ord)}{ext}"
                if candidate_key not in assigned:
                    filename = f"{sequence:03d}-{base}-{chr(suffix_ord)}{ext}"
                    base_key = candidate_key
                    resolved = True
                    break
            if not resolved:
                # Fallback: use sequence number as disambiguator
                candidate_key = f"{base}-{sequence}{ext}"
                filename = f"{sequence:03d}-{base}-{sequence}{ext}"
                base_key = candidate_key
        assigned.add(base_key)

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
    seen_urls: set[str] = set()
    assigned_filenames: set[str] = set()
    images_dir = temp_dir / "images"
    images_dir_created = False
    size_warning_emitted = False
    sequence = 0
    total_download_size = 0

    # Resource warning: image count threshold.
    unique_urls = {ref.url for ref in image_refs}
    if len(unique_urls) > IMAGE_COUNT_WARNING:
        logger.warning(
            "Article references %d unique images (threshold: %d)",
            len(unique_urls),
            IMAGE_COUNT_WARNING,
        )

    # Use a Session with redirect hop limiting.
    session = requests.Session()
    session.max_redirects = MAX_REDIRECT_HOPS

    for ref in image_refs:
        # Dedup by URL: skip if already seen (whether it succeeded or failed).
        if ref.url in seen_urls:
            logger.debug("Skipping duplicate URL: %s", ref.url)
            continue
        seen_urls.add(ref.url)

        sequence += 1

        # SSRF: validate initial URL before making ANY request.
        if _is_private_url(ref.url):
            logger.warning("Rejected %s: private/internal address", ref.url)
            continue

        # Download the image with retry logic.
        resp = None
        for attempt in range(MAX_IMAGE_RETRIES + 1):
            try:
                resp = _safe_get(
                    session,
                    ref.url,
                    headers={
                        "User-Agent": f"ohmd/{VERSION}",
                        "Referer": article_url,
                    },
                    timeout=(IMAGE_CONNECT_TIMEOUT, IMAGE_READ_TIMEOUT),
                )
                resp.raise_for_status()
                break  # Success — exit retry loop.
            except requests.TooManyRedirects as exc:
                # Redirect loops are persistent — no point retrying.
                logger.warning("Failed to download %s: %s", ref.url, exc)
                resp = None
                break
            except (requests.RequestException, OSError) as exc:
                if attempt < MAX_IMAGE_RETRIES:
                    delay = BACKOFF_DELAYS[attempt]
                    logger.info(
                        "Retry %d/%d for %s after error: %s (backoff %.1fs)",
                        attempt + 1,
                        MAX_IMAGE_RETRIES,
                        ref.url,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning(
                        "Failed to download %s after %d attempts: %s",
                        ref.url,
                        MAX_IMAGE_RETRIES + 1,
                        exc,
                    )
                    resp = None

        if resp is None:
            continue

        # Content-Type validation BEFORE downloading body (DESIGN.md section 4).
        content_type = resp.headers.get("Content-Type")
        if content_type:
            mime = content_type.split(";")[0].strip().lower()
            if not mime.startswith("image/"):
                logger.warning("Rejected %s: non-image Content-Type '%s'", ref.url, content_type)
                continue
        else:
            # No Content-Type header — accept only if URL has a known image extension.
            url_ext = _extract_url_extension(ref.url)
            if url_ext not in _KNOWN_EXTENSIONS:
                logger.warning(
                    "Rejected %s: no Content-Type and no known image extension",
                    ref.url,
                )
                continue

        # Download body only after Content-Type and SSRF checks pass.
        data = resp.content

        # Resolve filename.
        filename = _resolve_filename(ref.url, content_type, sequence, assigned_filenames)

        # Create images/ subfolder on first success (S-2).
        if not images_dir_created:
            images_dir.mkdir(parents=True, exist_ok=True)
            images_dir_created = True

        # Write file — convert OSError to FilesystemError for proper exit code.
        file_path = images_dir / filename
        try:
            file_path.write_bytes(data)
        except OSError as exc:
            raise FilesystemError(f"Failed to write image {filename}: {exc}") from exc

        image_size = len(data)
        result[ref.url] = ImageDownload(filename=filename, size=image_size)
        logger.info("Downloaded %s -> %s (%d bytes)", ref.url, filename, image_size)

        # Resource warning: single image size threshold.
        if image_size > SINGLE_IMAGE_SIZE_WARNING:
            logger.warning(
                "Image %s is %.1f MB (threshold: %d MB)",
                filename,
                image_size / (1024 * 1024),
                SINGLE_IMAGE_SIZE_WARNING // (1024 * 1024),
            )

        # Resource warning: cumulative download size threshold (emit once).
        total_download_size += image_size
        if total_download_size > TOTAL_DOWNLOAD_SIZE_WARNING and not size_warning_emitted:
            logger.warning(
                "Total download size %.1f MB exceeds threshold of %d MB",
                total_download_size / (1024 * 1024),
                TOTAL_DOWNLOAD_SIZE_WARNING // (1024 * 1024),
            )
            size_warning_emitted = True

    return result
