"""Publisher module tests: conflict, force, atomic write, rollback, stale cleanup."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 9")
def test_t08_folder_exists_no_force():
    """T-08: Output folder already exists, no --force: exit code 3,
    no files modified, existing folder untouched."""


@pytest.mark.skip(reason="Not yet implemented — slice 9")
def test_t09_folder_exists_with_force():
    """T-09: Output folder already exists, --force passed: old folder replaced,
    new output created."""


@pytest.mark.skip(reason="Not yet implemented — slice 8")
def test_t18_atomic_write_failure():
    """T-18: Atomic write: if write fails after images are downloaded,
    no final output folder exists at the target path."""


@pytest.mark.skip(reason="Not yet implemented — slice 9")
def test_t20_force_replacement_safety():
    """T-20: --force replacement safety: valid output folder exists,
    --force used, new run fails during fetch. Old folder remains intact."""


@pytest.mark.skip(reason="Not yet implemented — slice 10")
def test_t21_stale_temp_cleanup_safety():
    """T-21: Temp cleanup safety: a recently-modified temp directory exists
    (< 10 minutes old). Cleanup does not delete it."""
