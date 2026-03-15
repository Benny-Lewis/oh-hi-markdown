"""Publisher module tests: conflict, force, atomic write, rollback, stale cleanup."""

from pathlib import Path
from unittest.mock import patch

import pytest

from oh_hi_markdown.exceptions import FilesystemError
from oh_hi_markdown.publisher import publish


@pytest.mark.skip(reason="Not yet implemented — slice 9")
def test_t08_folder_exists_no_force():
    """T-08: Output folder already exists, no --force: exit code 3,
    no files modified, existing folder untouched."""


@pytest.mark.skip(reason="Not yet implemented — slice 9")
def test_t09_folder_exists_with_force():
    """T-09: Output folder already exists, --force passed: old folder replaced,
    new output created."""


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


@pytest.mark.skip(reason="Not yet implemented — slice 9")
def test_t20_force_replacement_safety():
    """T-20: --force replacement safety: valid output folder exists,
    --force used, new run fails during fetch. Old folder remains intact."""


@pytest.mark.skip(reason="Not yet implemented — slice 10")
def test_t21_stale_temp_cleanup_safety():
    """T-21: Temp cleanup safety: a recently-modified temp directory exists
    (< 10 minutes old). Cleanup does not delete it."""
