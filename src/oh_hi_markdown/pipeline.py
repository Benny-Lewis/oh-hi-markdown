"""Pipeline orchestrator — calls modules in sequence."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from oh_hi_markdown.images import download_all
from oh_hi_markdown.log import setup_logging, shutdown_logging
from oh_hi_markdown.parser import extract, rewrite
from oh_hi_markdown.provider import ContentProvider
from oh_hi_markdown.publisher import check_conflict, create_temp_dir, publish
from oh_hi_markdown.writer import assemble, generate_slug

logger = logging.getLogger("ohmd")


@dataclass
class RunResult:
    """Outcome of a pipeline run — enough for the CLI summary line."""

    outcome: str
    images_found: int
    images_downloaded: int
    images_failed: int
    output_path: Path


def run(
    url: str,
    output_dir: Path,
    force: bool,
    provider: ContentProvider,
) -> RunResult:
    """Execute the full pipeline for *url*.

    Implements DESIGN.md section 9 steps 2-9, 11-12.
    Step 1 (stale temp cleanup) is deferred to slice 10.

    Args:
        url: The article URL to fetch.
        output_dir: Parent directory where the output folder will be created.
        force: If True, overwrite an existing output folder.
        provider: The content provider (injected for testability).

    Returns:
        A :class:`RunResult` describing the outcome.
    """
    # Steps 3-4 run before step 2 because the slug (and thus the final path)
    # depends on the fetched title. This means a conflict check still waits for
    # the fetch, but no temp artifacts are created before the check.
    # Note: T-08 (slice 9) tests that no files are modified on conflict — the
    # fetch is a network call, not a file mutation, so this ordering is safe.

    # Step 3: Fetch markdown + metadata (provider)
    fetch_result = provider.fetch(url)

    # Step 4: Generate slug from fetch result (writer)
    slug, _title = generate_slug(fetch_result)
    final_path = Path(output_dir) / slug

    # Step 2: Check if final output path already exists (fail fast if not --force)
    check_conflict(final_path, force)

    # Step 1: Clean up stale temp directories — deferred to slice 10

    # Step 6: Create temp directory, attach log file handler
    temp_dir = create_temp_dir(Path(output_dir))
    setup_logging(temp_dir)

    logger.info("Fetched: %s", url)

    try:
        # Step 5: Extract image references (parser)
        image_refs = extract(fetch_result.markdown)
        unique_urls = {ref.url for ref in image_refs}
        images_found = len(unique_urls)

        # Step 7: Download images (images)
        if image_refs:
            downloads = download_all(image_refs, url, temp_dir)
        else:
            downloads = {}

        images_downloaded = len(downloads)
        images_failed = images_found - images_downloaded

        # Step 8: Rewrite markdown (parser)
        url_map = {orig_url: dl.filename for orig_url, dl in downloads.items()}
        markdown = rewrite(fetch_result.markdown, image_refs, url_map)

        # Step 9: Assemble article.md in temp directory (writer)
        assemble(fetch_result, markdown, str(temp_dir))

        logger.info("Assembled article.md")

    finally:
        # Step 10: Flush and close log file handler
        shutdown_logging()

    # Step 11: Publish temp directory to final path (publisher)
    publish(temp_dir, final_path)

    # Step 12: Return RunResult with outcome and stats
    outcome = "Partial success" if images_failed > 0 else "Success"
    return RunResult(
        outcome=outcome,
        images_found=images_found,
        images_downloaded=images_downloaded,
        images_failed=images_failed,
        output_path=final_path,
    )
