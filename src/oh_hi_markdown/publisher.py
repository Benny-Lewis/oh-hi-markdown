"""Temp directory lifecycle, atomic publish, --force rollback, stale cleanup."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from oh_hi_markdown.exceptions import FilesystemError

MARKER_FILENAME = ".ohmd-marker"
TEMP_PREFIX = ".ohmd-tmp-"


def create_temp_dir(parent_dir: Path) -> Path:
    """Create a temp directory with a marker file inside *parent_dir*.

    The directory is named ``.ohmd-tmp-{uuid}`` and contains a
    ``.ohmd-marker`` file written immediately on creation.

    Returns the path to the new temp directory.
    """
    temp_name = f"{TEMP_PREFIX}{uuid.uuid4()}"
    temp_path = parent_dir / temp_name
    temp_path.mkdir(parents=True, exist_ok=False)

    marker = temp_path / MARKER_FILENAME
    marker.write_text("ohmd temp directory\n", encoding="utf-8")

    return temp_path


def check_conflict(final_path: Path, force: bool) -> None:
    """Raise :class:`FilesystemError` if *final_path* exists and *force* is False.

    This is the pre-flight check described in DESIGN.md section 6 — it runs
    before any temp artifacts are created so a conflict exits cleanly with no
    leftover files.
    """
    if final_path.exists() and not force:
        raise FilesystemError(
            f"Output folder already exists: {final_path}\nUse --force to overwrite."
        )


def publish(temp_dir: Path, final_path: Path) -> None:
    """Atomically rename *temp_dir* to *final_path*.

    Wraps :func:`os.rename` and converts any :class:`OSError` into a
    :class:`FilesystemError`.
    """
    try:
        os.rename(temp_dir, final_path)
    except OSError as exc:
        raise FilesystemError(f"Failed to publish output to {final_path}: {exc}") from exc
