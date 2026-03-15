"""Pipeline orchestrator — calls modules in sequence."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from oh_hi_markdown.log import setup_logging, shutdown_logging
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

    Implements DESIGN.md section 9 steps 2-4, 6, 9-12.
    Steps 1, 5, 7, 8 are deferred to later slices.

    Args:
        url: The article URL to fetch.
        output_dir: Parent directory where the output folder will be created.
        force: If True, overwrite an existing output folder.
        provider: The content provider (injected for testability).

    Returns:
        A :class:`RunResult` describing the outcome.
    """
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
        # Step 5: Extract image references — deferred to slice 5
        # Step 7: Download images — deferred to slice 5
        # Step 8: Rewrite markdown — deferred to slice 5

        # Step 9: Assemble article.md in temp directory (writer)
        # For the no-image case, the markdown is passed through unchanged.
        assemble(fetch_result, fetch_result.markdown, str(temp_dir))

        logger.info("Assembled article.md")

    finally:
        # Step 10: Flush and close log file handler
        shutdown_logging()

    # Step 11: Publish temp directory to final path (publisher)
    publish(temp_dir, final_path)

    # Step 12: Return RunResult with outcome and stats
    return RunResult(
        outcome="Success",
        images_found=0,
        images_downloaded=0,
        images_failed=0,
        output_path=final_path,
    )
