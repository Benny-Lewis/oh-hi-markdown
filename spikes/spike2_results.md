# Spike 2 Results: Filesystem Flow Validation

**Date:** 2026-03-14
**Status:** All scenarios passed (6/6)

## Design Validated

The temp-directory, atomic-rename, and rollback filesystem flow works correctly on Linux.

## Test Results

| # | Scenario | Result | Details |
|---|----------|--------|---------|
| 1 | Normal publish | PASS | Files published, temp dir cleaned up, content verified |
| 2 | Folder exists, no force | PASS | PublishError raised, existing folder untouched, no temp dirs |
| 3 | Force replacement, success | PASS | Old folder replaced, backup cleaned up, new content verified |
| 4 | Force replacement, rename failure (rollback) | PASS | Backup restored, original intact, temp dir left for inspection |
| 5 | Stale temp cleanup | PASS | Stale (15min) removed, fresh (5min) kept |
| 6 | Marker file missing — skip | PASS | Dir without marker correctly skipped |

## Key Findings

1. **Atomic rename works:** `os.rename()` on the same filesystem (temp dir created in the same parent as the target) succeeds atomically on Linux. No partial states observed.

2. **Safe replacement flow is sound:** The backup-rename-swap-delete sequence works correctly. On rename failure, the backup is restored and the original directory is left intact. The temp dir is intentionally left in place for inspection.

3. **Stale cleanup is conservative:** Only directories matching the `.ohmd-tmp-*` pattern AND containing a `.ohmd-marker` file with mtime older than the threshold are removed. Directories without a marker are never touched, providing safety against deleting unrelated directories.

4. **No force = no damage:** When the target directory already exists and `force=False`, the operation fails with a clear error, the existing directory is completely untouched, and the temp dir is cleaned up (not left behind).

## Implementation Notes

- Temp dirs use the naming pattern `.ohmd-tmp-{uuid}` and are always created in the same parent directory as the final output path. This guarantees same-filesystem placement, which is required for atomic `os.rename()`.
- The `.ohmd-marker` file is written immediately after temp dir creation, before any output files. This makes it safe for the cleanup scanner to identify directories owned by oh-hi-markdown.
- Backup dirs use the pattern `{name}.ohmd-backup-{uuid}` and are deleted only after the final rename succeeds.
- The monkey-patching approach in test 4 reliably simulates a rename failure without requiring filesystem-level tricks.

## Conclusion

The proposed filesystem flow is validated and ready for production implementation.
