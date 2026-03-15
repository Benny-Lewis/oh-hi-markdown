"""Temp directory lifecycle, atomic publish, --force rollback, stale cleanup."""

from __future__ import annotations

import logging
import os
import shutil
import time
import uuid
from pathlib import Path

from oh_hi_markdown.exceptions import FilesystemError

MARKER_FILENAME = ".ohmd-marker"
TEMP_PREFIX = ".ohmd-tmp-"
BACKUP_PREFIX = ".ohmd-backup-"
STALE_TEMP_AGE_SECONDS = 600  # 10 minutes

logger = logging.getLogger("ohmd")


def cleanup_stale_temps(parent_dir: Path) -> None:
    """Delete stale ``.ohmd-tmp-*`` directories inside *parent_dir*.

    A directory is only deleted when both conditions are true:

    1. It contains a ``.ohmd-marker`` file.
    2. That marker file was last modified more than :data:`STALE_TEMP_AGE_SECONDS`
       seconds ago.

    Directories that lack a marker are never touched, regardless of age.
    Individual cleanup errors are logged and swallowed so that one failure
    does not block the others or abort the pipeline.
    """
    now = time.time()
    try:
        candidates = list(parent_dir.iterdir())
    except OSError as exc:
        logger.warning("Could not scan %s for stale temp dirs: %s", parent_dir, exc)
        return

    for entry in candidates:
        if not (entry.is_dir() and entry.name.startswith(TEMP_PREFIX)):
            continue
        marker = entry / MARKER_FILENAME
        if not marker.exists():
            continue
        try:
            marker_age = now - marker.stat().st_mtime
            if marker_age > STALE_TEMP_AGE_SECONDS:
                shutil.rmtree(entry)
                logger.info("Removed stale temp directory: %s (age %.0fs)", entry, marker_age)
        except OSError as exc:
            logger.warning("Could not clean up stale temp dir %s: %s", entry, exc)


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


def _publish_with_force(temp_dir: Path, final_path: Path) -> None:
    """Replace an existing *final_path* with *temp_dir* using safe backup/rollback.

    Implements the --force replacement sequence from DESIGN.md section 6:

    1. Rename existing folder to a backup: ``{folder}.ohmd-backup-{uuid}``
    2. Rename temp directory to the final output path.
    3. If step 2 succeeds: delete the backup folder.
    4. If step 2 fails: restore the backup to the original name, leave the
       temp directory in place, and raise :class:`FilesystemError`.
    """
    backup_name = f"{final_path.name}{BACKUP_PREFIX}{uuid.uuid4()}"
    backup_path = final_path.parent / backup_name

    # Step 1: Rename existing folder to backup.
    try:
        os.rename(final_path, backup_path)
    except OSError as exc:
        raise FilesystemError(f"Failed to create backup of {final_path}: {exc}") from exc

    # Step 2: Rename temp directory to final path.
    try:
        os.rename(temp_dir, final_path)
    except OSError as exc:
        # Step 2 failed — restore backup.
        try:
            os.rename(backup_path, final_path)
        except OSError:
            pass  # Best effort; original error is more important.
        raise FilesystemError(f"Failed to publish output to {final_path}: {exc}") from exc

    # Step 3: Delete backup.
    shutil.rmtree(backup_path, ignore_errors=True)


def publish(temp_dir: Path, final_path: Path, *, force: bool = False) -> None:
    """Rename *temp_dir* to *final_path*, handling the --force case.

    When *force* is ``True`` and *final_path* already exists, delegates to
    :func:`_publish_with_force` for safe backup-and-replace.  Otherwise
    performs a simple :func:`os.rename`.

    Wraps any :class:`OSError` into a :class:`FilesystemError`.
    """
    if force and final_path.exists():
        _publish_with_force(temp_dir, final_path)
        return

    try:
        os.rename(temp_dir, final_path)
    except OSError as exc:
        raise FilesystemError(f"Failed to publish output to {final_path}: {exc}") from exc
