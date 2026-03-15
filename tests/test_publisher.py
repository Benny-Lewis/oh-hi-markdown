"""Publisher module tests: conflict, force, atomic write, rollback, stale cleanup."""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from oh_hi_markdown.exceptions import FilesystemError, ProviderHTTPError
from oh_hi_markdown.jina import JinaProvider
from oh_hi_markdown.pipeline import run
from oh_hi_markdown.publisher import MARKER_FILENAME, TEMP_PREFIX, cleanup_stale_temps, publish

TEST_URL = "https://example.com/test-article"
JINA_URL = f"https://r.jina.ai/{TEST_URL}"


def _jina_no_images_response():
    """Jina JSON response with title 'Test Article Title' and no images."""
    return {
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


@responses.activate
def test_t08_folder_exists_no_force(tmp_path: Path) -> None:
    """T-08: Output folder already exists, no --force: exit code 3,
    no files modified, existing folder untouched."""
    # Pre-create output folder with a known file inside.
    existing_folder = tmp_path / "test-article-title"
    existing_folder.mkdir()
    sentinel_file = existing_folder / "old-content.txt"
    sentinel_file.write_text("do not touch\n", encoding="utf-8")

    # Mock Jina response (slug resolves to "test-article-title").
    responses.add(responses.GET, JINA_URL, json=_jina_no_images_response(), status=200)

    # Run pipeline without --force — should raise FilesystemError.
    with pytest.raises(FilesystemError, match="--force") as exc_info:
        run(
            url=TEST_URL,
            output_dir=tmp_path,
            force=False,
            provider=JinaProvider(),
        )

    # Error message suggests --force (gap O-3).
    assert "--force" in str(exc_info.value)

    # Existing folder and its contents must be untouched.
    assert existing_folder.exists()
    assert sentinel_file.read_text(encoding="utf-8") == "do not touch\n"

    # Fetch happened (slug depends on it), so at least 1 HTTP call.
    assert len(responses.calls) >= 1

    # No temp directories were created (conflict check runs before create_temp_dir).
    temp_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith(TEMP_PREFIX)]
    assert len(temp_dirs) == 0


@responses.activate
def test_t09_folder_exists_with_force(tmp_path: Path) -> None:
    """T-09: Output folder already exists, --force passed: old folder replaced,
    new output created."""
    # Pre-create output folder with an old file.
    existing_folder = tmp_path / "test-article-title"
    existing_folder.mkdir()
    old_file = existing_folder / "old-content.txt"
    old_file.write_text("stale data\n", encoding="utf-8")

    # Mock Jina with a no-image response.
    responses.add(responses.GET, JINA_URL, json=_jina_no_images_response(), status=200)

    result = run(
        url=TEST_URL,
        output_dir=tmp_path,
        force=True,
        provider=JinaProvider(),
    )

    # Output folder now contains new content.
    output_path = result.output_path
    assert output_path.exists()
    assert (output_path / "article.md").exists()

    # Old file is gone.
    assert not (output_path / "old-content.txt").exists()

    # No backup directories remain.
    backup_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and ".ohmd-backup-" in p.name]
    assert len(backup_dirs) == 0

    # No temp directories remain.
    temp_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith(TEMP_PREFIX)]
    assert len(temp_dirs) == 0


def test_t18_atomic_write_failure(tmp_path: Path) -> None:
    """T-18: Atomic write: if write fails after images are downloaded,
    no final output folder exists at the target path."""
    # Simulate a post-download temp dir with real content
    temp_dir = tmp_path / ".ohmd-tmp-test"
    temp_dir.mkdir()
    (temp_dir / ".ohmd-marker").write_text("ohmd temp directory\n", encoding="utf-8")
    (temp_dir / "index.md").write_text("# Hello\n", encoding="utf-8")
    (temp_dir / "image.png").write_bytes(b"\x89PNG")

    final_path = tmp_path / "output"

    # Patch os.rename to simulate a filesystem failure during atomic rename
    with patch("oh_hi_markdown.publisher.os.rename", side_effect=OSError("cross-device link")):
        with pytest.raises(FilesystemError, match="Failed to publish output"):
            publish(temp_dir, final_path)

    # Final output path must not exist
    assert not final_path.exists(), "final_path must not exist after a failed rename"

    # Temp dir and its contents must still be present
    assert temp_dir.exists(), "temp_dir must still exist after a failed rename"
    assert (temp_dir / "index.md").exists(), "temp_dir contents must be intact"


@responses.activate
def test_t20_force_replacement_safety(tmp_path: Path) -> None:
    """T-20: --force replacement safety: valid output folder exists,
    --force used, new run fails during fetch. Old folder remains intact."""
    # Pre-create output folder with known content.
    existing_folder = tmp_path / "test-article-title"
    existing_folder.mkdir()
    sentinel_file = existing_folder / "precious-data.txt"
    sentinel_file.write_text("must survive\n", encoding="utf-8")

    # Mock Jina to return HTTP 500 — provider raises ProviderHTTPError.
    responses.add(responses.GET, JINA_URL, json={"error": "server error"}, status=500)

    with pytest.raises(ProviderHTTPError):
        run(
            url=TEST_URL,
            output_dir=tmp_path,
            force=True,
            provider=JinaProvider(),
        )

    # Existing folder must be completely intact.
    assert existing_folder.exists()
    assert sentinel_file.exists()
    assert sentinel_file.read_text(encoding="utf-8") == "must survive\n"

    # No temp directories were created (provider fails before create_temp_dir).
    temp_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith(TEMP_PREFIX)]
    assert len(temp_dirs) == 0


def test_t21_stale_temp_cleanup_safety(tmp_path: Path) -> None:
    """T-21: Stale temp cleanup:
    - `.ohmd-tmp-xxx` with marker < 10 min old → NOT deleted.
    - `.ohmd-tmp-yyy` with marker > 10 min old → deleted.
    - `.ohmd-tmp-zzz` without a marker → NOT deleted (regardless of age).
    """
    # Fresh temp dir: has marker, mtime = now (< 10 min old).
    fresh_dir = tmp_path / f"{TEMP_PREFIX}fresh"
    fresh_dir.mkdir()
    fresh_marker = fresh_dir / MARKER_FILENAME
    fresh_marker.write_text("ohmd temp directory\n", encoding="utf-8")

    # Stale temp dir: has marker, mtime set to 11 minutes ago.
    stale_dir = tmp_path / f"{TEMP_PREFIX}stale"
    stale_dir.mkdir()
    stale_marker = stale_dir / MARKER_FILENAME
    stale_marker.write_text("ohmd temp directory\n", encoding="utf-8")
    stale_time = time.time() - 660  # 11 minutes ago
    os.utime(stale_marker, (stale_time, stale_time))

    # No-marker temp dir: name matches prefix but has no .ohmd-marker.
    nomarker_dir = tmp_path / f"{TEMP_PREFIX}nomarker"
    nomarker_dir.mkdir()
    (nomarker_dir / "random-file.txt").write_text("contents\n", encoding="utf-8")

    cleanup_stale_temps(tmp_path)

    # Stale dir (has marker, > 10 min old) must be deleted.
    assert not stale_dir.exists(), "stale dir should have been removed"

    # Fresh dir (has marker, < 10 min old) must NOT be deleted.
    assert fresh_dir.exists(), "fresh dir must not be removed"

    # No-marker dir must NOT be deleted.
    assert nomarker_dir.exists(), "dir without marker must not be removed"
