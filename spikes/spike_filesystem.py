#!/usr/bin/env python3
"""
Spike 2: Validate temp-directory -> atomic-rename -> rollback filesystem flow.

Tests the publish, force-replace, and stale-temp-cleanup patterns for oh-hi-markdown.
"""

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Implementation under test
# ---------------------------------------------------------------------------

class PublishError(Exception):
    pass


def publish(output_dir: Path, files: dict[str, str], force: bool = False) -> Path:
    """
    Publish files to output_dir using temp-dir + atomic-rename.

    Args:
        output_dir: Final destination path.
        files: Mapping of relative filename -> content.
        force: If True, replace an existing output_dir via safe backup flow.

    Returns:
        The final output_dir path.

    Raises:
        PublishError: If output_dir exists and force is False, or if
                      the rename fails and rollback is needed.
    """
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Build everything in a temp dir inside the same parent (same filesystem).
    tmp_name = f".ohmd-tmp-{uuid.uuid4()}"
    tmp_dir = parent / tmp_name
    tmp_dir.mkdir()

    # Step 2: Write marker immediately.
    marker = tmp_dir / ".ohmd-marker"
    marker.write_text(f"created={time.time()}\n")

    # Write all output files.
    for rel_path, content in files.items():
        dest = tmp_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    # Step 3: Rename to final path.
    if output_dir.exists():
        if not force:
            # Clean up temp dir since we're aborting.
            shutil.rmtree(tmp_dir)
            raise PublishError(
                f"Output directory already exists: {output_dir}. Use force=True to replace."
            )

        # --- Force safe replacement flow ---
        backup_name = f"{output_dir.name}.ohmd-backup-{uuid.uuid4()}"
        backup_dir = parent / backup_name

        # 2. Rename existing folder to backup.
        try:
            os.rename(output_dir, backup_dir)
        except OSError as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise PublishError(
                f"Failed to back up existing directory: {e}"
            )

        # 3. Rename temp dir to final path.
        try:
            os.rename(tmp_dir, output_dir)
        except OSError:
            # 5. Restore backup, leave temp dir in place for inspection.
            try:
                os.rename(backup_dir, output_dir)
            except OSError as rollback_err:
                raise PublishError(
                    f"Rename failed AND rollback failed: {rollback_err}. "
                    f"Backup left at {backup_dir}, temp dir at {tmp_dir}. "
                    f"Manual recovery required."
                )
            raise PublishError(
                f"Rename failed. Restored backup to {output_dir}. "
                f"Temp dir left at {tmp_dir} for inspection."
            )

        # 4. Success — delete backup.
        shutil.rmtree(backup_dir)
    else:
        os.rename(tmp_dir, output_dir)

    return output_dir


def cleanup_stale_temps(parent: Path, max_age_seconds: float = 600) -> list[Path]:
    """
    Scan parent for .ohmd-tmp-* dirs and remove stale ones.

    A temp dir is stale if:
      (a) it contains a .ohmd-marker file, AND
      (b) that marker's mtime is older than max_age_seconds.

    Dirs without a marker are skipped (not ours, or corrupted).

    Returns list of removed directories.
    """
    removed = []

    if not parent.exists():
        return removed

    now = time.time()

    for entry in parent.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith(".ohmd-tmp-"):
            continue

        marker = entry / ".ohmd-marker"
        if not marker.exists():
            # No marker — skip, not safe to delete.
            continue

        age = now - marker.stat().st_mtime
        if age > max_age_seconds:
            shutil.rmtree(entry)
            removed.append(entry)

    return removed


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

results: list[tuple[str, bool, str]] = []


def run_test(name: str, fn):
    """Run a test function in an isolated temp directory."""
    workspace = Path(tempfile.mkdtemp(prefix="ohmd-spike2-"))
    try:
        passed, detail = fn(workspace)
        results.append((name, passed, detail))
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    except Exception as exc:
        results.append((name, False, f"Unexpected exception: {exc}"))
        print(f"  [FAIL] {name}: Unexpected exception: {exc}")
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

def test_normal_publish(workspace: Path) -> tuple[bool, str]:
    """Scenario 1: Normal publish to a new directory."""
    output = workspace / "my-site"
    files = {"index.html": "<h1>Hello</h1>", "style.css": "body {}"}

    publish(output, files)

    # Verify final path exists with correct content.
    if not output.is_dir():
        return False, "Output directory does not exist after publish"
    if (output / "index.html").read_text() != "<h1>Hello</h1>":
        return False, "index.html content mismatch"
    if (output / "style.css").read_text() != "body {}":
        return False, "style.css content mismatch"

    # Verify no temp dirs remain.
    temps = [p for p in workspace.iterdir() if p.name.startswith(".ohmd-tmp-")]
    if temps:
        return False, f"Temp dir(s) left behind: {temps}"

    # Verify marker file is NOT in the final output (it was in temp dir, renamed).
    # The marker IS expected to be present since the whole dir was renamed.
    # This is fine — it's an implementation detail.

    return True, "Files published, temp dir cleaned up, content verified"


def test_exists_no_force(workspace: Path) -> tuple[bool, str]:
    """Scenario 2: Folder already exists, no force — should fail cleanly."""
    output = workspace / "my-site"
    output.mkdir()
    sentinel = output / "existing.txt"
    sentinel.write_text("do not touch")

    try:
        publish(output, {"index.html": "<h1>New</h1>"}, force=False)
        return False, "Expected PublishError but publish succeeded"
    except PublishError:
        pass

    # Existing folder must be untouched.
    if not sentinel.exists():
        return False, "Existing file was deleted"
    if sentinel.read_text() != "do not touch":
        return False, "Existing file content was modified"

    # No temp dirs should remain.
    temps = [p for p in workspace.iterdir() if p.name.startswith(".ohmd-tmp-")]
    if temps:
        return False, f"Temp dir(s) left behind: {temps}"

    return True, "PublishError raised, existing folder untouched, no temp dirs"


def test_force_replacement_success(workspace: Path) -> tuple[bool, str]:
    """Scenario 3: Force replacement succeeds."""
    output = workspace / "my-site"
    output.mkdir()
    (output / "old.txt").write_text("old content")

    publish(output, {"index.html": "<h1>New</h1>"}, force=True)

    if not output.is_dir():
        return False, "Output directory missing after force publish"
    if (output / "index.html").read_text() != "<h1>New</h1>":
        return False, "New content not present"
    if (output / "old.txt").exists():
        return False, "Old file still present — replacement didn't happen"

    # No backups should remain.
    backups = [p for p in workspace.iterdir() if ".ohmd-backup-" in p.name]
    if backups:
        return False, f"Backup dir(s) left behind: {backups}"

    # No temp dirs should remain.
    temps = [p for p in workspace.iterdir() if p.name.startswith(".ohmd-tmp-")]
    if temps:
        return False, f"Temp dir(s) left behind: {temps}"

    return True, "Old folder replaced, backup cleaned up, new content verified"


def test_force_replacement_rename_failure(workspace: Path) -> tuple[bool, str]:
    """Scenario 4: Force replacement where step 3 (rename) fails.

    We simulate this by placing a regular FILE at the target path after the
    existing dir is backed up. Since os.rename() of a directory onto an
    existing file fails on Linux, this triggers the rollback path.

    Implementation note: We need to intercept between the backup rename and
    the temp-dir rename. We do this by creating a scenario where a file
    occupies the target name, which causes os.rename(tmp_dir, output_dir) to
    fail with OSError (not a directory / file exists).
    """
    output = workspace / "my-site"
    output.mkdir()
    (output / "precious.txt").write_text("precious data")

    # We'll monkey-patch os.rename to simulate failure on the second call.
    original_rename = os.rename
    call_count = [0]

    def patched_rename(src, dst):
        call_count[0] += 1
        if call_count[0] == 2:
            # This is the temp->final rename. Simulate failure.
            raise OSError("Simulated rename failure")
        return original_rename(src, dst)

    try:
        os.rename = patched_rename
        try:
            publish(output, {"index.html": "<h1>New</h1>"}, force=True)
            return False, "Expected PublishError but publish succeeded"
        except PublishError:
            pass
    finally:
        os.rename = original_rename

    # Original folder should be restored.
    if not output.is_dir():
        return False, "Original folder not restored after rollback"
    if not (output / "precious.txt").exists():
        return False, "Original file missing after rollback"
    if (output / "precious.txt").read_text() != "precious data":
        return False, "Original file content corrupted after rollback"

    # Temp dir should still exist (left for inspection).
    temps = [p for p in workspace.iterdir() if p.name.startswith(".ohmd-tmp-")]
    if not temps:
        return False, "Temp dir was cleaned up — should be left for inspection"

    return True, "Backup restored, original intact, temp dir left for inspection"


def test_stale_temp_cleanup(workspace: Path) -> tuple[bool, str]:
    """Scenario 5: Stale temp cleanup based on marker mtime."""
    # Create a stale temp dir (marker mtime 15 minutes ago).
    stale = workspace / f".ohmd-tmp-{uuid.uuid4()}"
    stale.mkdir()
    stale_marker = stale / ".ohmd-marker"
    stale_marker.write_text("old")
    fifteen_min_ago = time.time() - 15 * 60
    os.utime(stale_marker, (fifteen_min_ago, fifteen_min_ago))

    # Create a fresh temp dir (marker mtime 5 minutes ago).
    fresh = workspace / f".ohmd-tmp-{uuid.uuid4()}"
    fresh.mkdir()
    fresh_marker = fresh / ".ohmd-marker"
    fresh_marker.write_text("new")
    five_min_ago = time.time() - 5 * 60
    os.utime(fresh_marker, (five_min_ago, five_min_ago))

    removed = cleanup_stale_temps(workspace, max_age_seconds=600)

    if stale.exists():
        return False, "Stale temp dir was NOT removed"
    if not fresh.exists():
        return False, "Fresh temp dir was incorrectly removed"
    if len(removed) != 1:
        return False, f"Expected 1 removal, got {len(removed)}"
    if removed[0] != stale:
        return False, f"Wrong dir removed: {removed[0]}"

    return True, "Stale (15min) removed, fresh (5min) kept"


def test_marker_missing(workspace: Path) -> tuple[bool, str]:
    """Scenario 6: Temp dir without marker file — cleanup should skip it."""
    no_marker = workspace / f".ohmd-tmp-{uuid.uuid4()}"
    no_marker.mkdir()
    # Write some file but NOT .ohmd-marker.
    (no_marker / "random.txt").write_text("not a marker")

    removed = cleanup_stale_temps(workspace, max_age_seconds=0)

    if not no_marker.exists():
        return False, "Dir without marker was incorrectly removed"
    if removed:
        return False, f"cleanup returned removed dirs but shouldn't have: {removed}"

    return True, "Dir without marker correctly skipped"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Spike 2: Filesystem flow validation")
    print("=" * 60)
    print()

    run_test("1. Normal publish", test_normal_publish)
    run_test("2. Folder exists, no force", test_exists_no_force)
    run_test("3. Force replacement, success", test_force_replacement_success)
    run_test("4. Force replacement, rename failure (rollback)", test_force_replacement_rename_failure)
    run_test("5. Stale temp cleanup", test_stale_temp_cleanup)
    run_test("6. Marker file missing — skip", test_marker_missing)

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} passed")

    if passed == total:
        print("All scenarios validated successfully.")
    else:
        print("Some scenarios FAILED — see details above.")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())
