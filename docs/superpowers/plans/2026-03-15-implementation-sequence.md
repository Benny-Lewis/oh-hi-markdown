# Implementation Sequence Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the ordered implementation sequence for oh-hi-markdown's 13 vertical slices, with per-slice scope, files, tests, dependencies, and done criteria — the roadmap for PLAN.md step 7.

**Architecture:** Linear pipeline of 9 modules (cli → pipeline → provider/jina → parser → images → writer → publisher → log), plus config and exceptions (already implemented). Each slice adds a layer of functionality, tested via 28 stubbed test cases that go from `@pytest.mark.skip` to green.

**Tech Stack:** Python 3.10+, requests, python-dateutil, pytest, responses, ruff

**Reference docs:**
- `DESIGN.md` — module boundaries, interfaces, data flow
- `REQUIREMENTS.md` — acceptance criteria (F-*, D-*, P-*, R-*, S-*, L-*, O-*)
- `docs/superpowers/specs/2026-03-14-test-strategy-design.md` — test cases, fixtures, traceability map
- `PLAN.md` — development lifecycle (this plan covers step 6)

---

## Dependency Graph

```
Slice 1 (CLI)           ──────────────────┐
Slice 2 (Provider/Jina) ────────┐         │
                                ▼         │
Slice 3 (Writer)        ───────►│         │
                                ▼         ▼
Slice 4 (No-image path) ◄──────┴─────────┘
         │
         ▼
Slice 5 (Parser + images)
         │
    ┌────┼────┐
    ▼    ▼    ▼
  S6   S7   S13    ← independent of each other
    │    │
    └──┬─┘
       ▼
Slice 8 (Atomic publish) ◄── also reachable from S4 directly
       │
    ┌──┴──┐
    ▼     ▼
  S9    S10

Slice 11 (Logging) ◄── depends on S4
Slice 12 (Aliases) ◄── depends on S1
```

**Key observations:**
- Slices 1 and 2 are independent — can be built in parallel
- Slices 6, 7, 13 are independent of each other (all depend on S5)
- Slices 8, 11, 12 are independent of each other (depend on S4 or S1)
- Critical path: 1 → 2 → 3 → 4 → 5 → 6/7 → 8 → 9 → 10

---

## Cross-Cutting Patterns

These patterns apply to every slice. Individual slices reference them by name rather than repeating.

**Error handling:** All modules raise exceptions (from `exceptions.py`). Only `cli.py` catches them and maps to exit codes. No module catches another module's exceptions.

**Logging:** All modules use `logging.getLogger(__name__)`. Until slice 11, logging is minimal (basic `StreamHandler`). After slice 11, full formatting and redaction.

**Testing:** All tests use `@responses.activate` for HTTP mocking and `tmp_path` for filesystem. Shared fixtures in `conftest.py`. Tests are self-contained.

**Imports:** Modules import from `config.py` for constants and `exceptions.py` for error types. Pipeline receives concrete implementations via parameter (dependency injection).

**TDD cycle:** For each slice: remove `@pytest.mark.skip` → implement test body → run to confirm failure → write minimal implementation → run to confirm pass → commit.

**Already implemented:** `config.py` (all constants) and `exceptions.py` (full hierarchy). These are ready to import.

---

## Chunk 1: Foundation Slices (1–4)

### Task 1: Slice 1 — CLI shell + URL validation + exit codes

**Scope:** Complete the CLI module with URL validation, error messaging, and correct exit codes. Entry point that all subsequent slices depend on for CLI-level behavior.

**Files:**
- Modify: `src/oh_hi_markdown/cli.py` — add `validate_url()` with scheme check, localhost/loopback/RFC1918/link-local rejection using `urllib.parse` + `ipaddress`. Update `main()` to call validation before pipeline.
- Modify: `tests/test_cli.py` — remove `@pytest.mark.skip` from T-10 and T-24, implement test bodies.

**Tests turned green:** T-10, T-24

**Acceptance criteria:** URL validation (pre-fetch gate)

**Dependencies:** None

**Done criteria:**
- [ ] T-10 passes: URL without scheme (e.g., `example.com`) → exit code 1, descriptive error, no HTTP requests
- [ ] T-24 passes: private IPs (`192.168.1.1`, `10.0.0.1`, `172.16.0.1`), localhost, `127.0.0.1`, `::1`, link-local (`169.254.x.x`) → exit code 1
- [ ] Valid URL (`https://example.com/article`) passes validation (does not exit 1)
- [ ] `main()` exits 4 (not 0) for valid URLs when pipeline is not yet wired — temporary until slice 4
- [ ] `pytest` shows 2 passed, 26 skipped, no regressions

**Key decisions:**
- `validate_url(url: str) -> str | None` — returns error message or `None`. Pure function, easy to test directly.
- Tests call `validate_url()` directly (unit-level), not through argparse.
- `main()` should exit 4 for "not yet implemented" pipeline (not exit 0), since the pipeline doesn't work yet. This is temporary until slice 4 wires it up.
- If stash doesn't apply cleanly, implement from scratch using the steps above — the plan is self-contained.

**Stashed WIP:** `git stash list` shows `stash@{0}` with ~90% of this work done (URL validation + README updates from a previous session). Run `git stash pop` on the implementation branch, review against this plan, then write tests and commit. The stash was created on `scaffold/project-setup` but applies cleanly to `main`.

**Complexity:** S (Small)

---

### Task 2: Slice 2 — Provider interface + Jina fetch + error handling

**Scope:** Define `ContentProvider` protocol and `FetchResult` dataclass in `provider.py`. Implement `JinaProvider` in `jina.py` with request construction, response parsing, and all 5 error paths. Update `conftest.py` fixture.

**Files:**
- Modify: `src/oh_hi_markdown/provider.py` — add `FetchResult` dataclass (fields: `markdown`, `title`, `author`, `date`, `description`, `source_url`) and `ContentProvider` Protocol with `fetch(url) -> FetchResult`.
- Modify: `src/oh_hi_markdown/jina.py` — implement `JinaProvider` class with `fetch()`: URL construction (`https://r.jina.ai/{url}`), headers (`Accept: application/json`, `X-With-Generated-Alt: true`, `User-Agent: ohmd/{version}`, conditional `Authorization: Bearer`), timeouts from config, JSON response parsing, author extraction (metadata priority: `author` → `article:author` → `og:author` → `citation_author`), date extraction (`publishedTime` → `article:published_time` → `date` → `DC.date`), and 5 exception paths.
- Modify: `tests/test_provider.py` — remove `@pytest.mark.skip` from T-11, T-12, T-27, implement with `@responses.activate`.
- Modify: `tests/conftest.py` — update `sample_fetch_result` to return real `FetchResult` instead of `pytest.skip()`. Also update `jina_success_response` to include a `metadata` dict inside `data` with author/date keys for metadata fallback testing.

**Tests turned green:** T-11, T-12, T-27

**Acceptance criteria:** F-4 (HTTP error), F-5 (rate limit), F-6 (empty content)

**Dependencies:** None (provider tests don't go through CLI)

**Done criteria:**
- [ ] T-11 passes: Jina 500 → `ProviderHTTPError(status_code=500)` raised
- [ ] T-12 passes: Jina 429 → `ProviderRateLimitError` raised
- [ ] T-27 passes: Jina 200 with empty content → `ProviderEmptyContentError` raised
- [ ] Gap F-3: T-11 also asserts `JINA_API_KEY` Bearer token is included in request headers when env var set
- [ ] Gap F-4: separate test case within T-11 (or parameterized) asserts `ProviderUnreachableError` for `ConnectionError` — distinct code path from the HTTP 500 case, keep test logic separated
- [ ] `conftest.sample_fetch_result` returns a real `FetchResult` with title/author/date/description/source_url/markdown (with 3 image refs)
- [ ] `JinaProvider(api_key=...)` accepts optional key parameter for testability
- [ ] `pytest` shows 5 passed (T-10, T-24, T-11, T-12, T-27), 23 skipped

**Key decisions:**
- `JinaProvider.__init__(api_key: str | None = None)` — defaults to `os.environ.get(JINA_API_KEY_ENV)`. Enables testing without env var manipulation.
- `FetchResult.source_url` holds the original input URL, not Jina's canonical URL.
- Author/date extraction happens in the Jina provider, not the writer — keeps the provider boundary clean per DESIGN.md.

**Complexity:** M (Medium)

---

### Task 3: Slice 3 — Metadata extraction + front matter generation + slug/folder naming

**Scope:** Implement the writer module: slug generation with full 5-priority title fallback chain, front matter serialization with field ordering and omission rules. Does NOT write to filesystem — that comes in slice 4.

**Files:**
- Modify: `src/oh_hi_markdown/writer.py` — implement `generate_slug(fetch_result: FetchResult) -> str` (slugification: lowercase, sanitize `[a-z0-9-]`, collapse hyphens, truncate to 80 chars; fallback chain: title → transliterated title → H1 → URL path → timestamp), `generate_front_matter(fetch_result, downloaded_timestamp) -> str` (manual YAML per ADR-02, field order: title/author/date/source_url/description/downloaded/tool, omit None fields), and `assemble(fetch_result, markdown, temp_dir)` (concatenate front matter + markdown, write to `article.md`).
- Modify: `tests/test_writer.py` — remove `@pytest.mark.skip` from T-13, T-14, T-25, implement with crafted `FetchResult` inputs.

**Tests turned green:** T-13, T-14, T-25

**Acceptance criteria:** S-1 (partial — slug/naming), S-3 (front matter format)

**Dependencies:** Slice 2 (needs `FetchResult` dataclass from `provider.py`)

**Done criteria:**
- [ ] T-13 passes: title `"My Article! (2026)"` → slug `my-article-2026`, front matter title is the original
- [ ] T-14 passes: title=None + markdown has `# Heading` → slug from H1. No title + no H1 + URL path → slug from URL. All empty → timestamp fallback `article-YYYYMMDD-HHMMSS`
- [ ] T-25 passes: author=None, description=None → those fields omitted (not blank). Fields in order: title, author, date, source_url, description, downloaded, tool
- [ ] Date normalization: `"Wed, 11 Mar 2026 19:06:45 GMT"` → `"2026-03-11"` (via `python-dateutil`)
- [ ] YAML escape function handles `"` and `\` in values
- [ ] `pytest` shows 8 passed, 20 skipped

**Key decisions:**
- `generate_slug()` and `generate_front_matter()` are separate functions — pipeline needs slug early (to determine output path for conflict check) before assembling the full article.
- Non-ASCII transliteration: `unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()` — stdlib only.
- Manual YAML serialization per ADR-02: deterministic field order, consistent quoting, exact spec match.

**Complexity:** M (Medium)

---

### Task 4: Slice 4 — No-image happy path (end-to-end)

**Scope:** Wire the full pipeline for the no-image case: CLI → pipeline → provider → writer → publisher. Implement basic publisher (temp dir, marker file, atomic rename) and minimal logging. First slice where the tool actually does something end-to-end.

**Files:**
- Modify: `src/oh_hi_markdown/pipeline.py` — implement `run(url, output_dir, force, provider) -> RunResult`. Define `RunResult` dataclass (outcome, images_found, images_downloaded, images_failed, output_path). Implement DESIGN.md steps 1-6, 9-12 (skip image steps 7-8 when no images). Create temp dir, call writer, call publisher.
- Modify: `src/oh_hi_markdown/publisher.py` — implement `create_temp_dir(parent_dir) -> Path` (creates `.ohmd-tmp-{uuid}` with `.ohmd-marker`), `check_conflict(final_path, force)` (raises `FilesystemError` if exists and not force), `publish(temp_dir, final_path)` (`os.rename`). Basic versions only — no `--force` replacement, no stale cleanup, no rollback.
- Modify: `src/oh_hi_markdown/cli.py` — wire `main()` to call `pipeline.run()`. Add try/except for `ProviderError` (exit 2) and `FilesystemError` (exit 3). Import `JinaProvider` and pass to pipeline.
- Modify: `src/oh_hi_markdown/log.py` — implement minimum viable `setup_logging(temp_dir)`: create `ohmd.log` file handler + stderr stream handler. Basic formatting only — full `✓`/`⚠` and redaction come in slice 11.
- Modify: `tests/test_pipeline.py` — remove `@pytest.mark.skip` from T-02. Mock Jina (no images in response), verify `article.md` exists with correct front matter, no `images/` folder, outcome "Success".

**Tests turned green:** T-02

**Acceptance criteria:** F-1, S-1, S-2 (no images case), S-3, O-1, O-2

**Dependencies:** Slices 1, 2, 3

**Done criteria:**
- [ ] T-02 passes: mock Jina response with no images → `article.md` in output folder, no `images/` subfolder, `ohmd.log` exists, exit code 0
- [ ] Front matter in `article.md` matches spec field ordering
- [ ] `RunResult` has outcome="Success", images_found=0, images_downloaded=0, images_failed=0
- [ ] `check_conflict` raises `FilesystemError` when folder exists and `--force` not passed (informally verified — formal test is T-08 in slice 9)
- [ ] CLI maps `ProviderError` to exit 2, `FilesystemError` to exit 3
- [ ] `pytest` shows 9 passed, 19 skipped

**Key decisions:**
- `pipeline.run()` receives a `ContentProvider` instance (dependency injection). CLI creates `JinaProvider` and passes it in. Tests pass a mock provider or use `@responses.activate`. Note: DESIGN.md shows `run(url, output_dir, force)` without a `provider` parameter — the added parameter is a deviation that enables testability. The CLI creates the concrete provider.
- `RunResult` lives in `pipeline.py`.
- `log.setup_logging(temp_dir)` creates file handler at step 6 (after temp dir creation). Steps 1-5 log to console only.
- Publisher uses `os.rename()` — atomic on same-filesystem (guaranteed by temp dir placement).

**Complexity:** L (Large) — first integration slice, wires 5 modules

---

## Chunk 2: Image Pipeline (Slices 5–7)

### Task 5: Slice 5 — Markdown image parsing + basic image download + link rewriting

**Scope:** Implement parser module (extract + rewrite) and basic image download flow. After this slice, the full happy path with images works.

**Files:**
- Modify: `src/oh_hi_markdown/parser.py` — implement `ImageRef` dataclass (alt, url, original_match), `IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\(([^)]+)\)', re.DOTALL)`, `extract(markdown) -> list[ImageRef]` (filter to http/https scheme only), `rewrite(markdown, image_refs, url_map) -> str` (replace `original_match` with `![alt](./images/filename)`).
- Modify: `src/oh_hi_markdown/images.py` — implement `ImageDownload` dataclass (filename, size), `download_all(image_refs, article_url, temp_dir) -> dict[str, ImageDownload]`. Basic version: sequential download, dedup by URL (first occurrence), filename resolution (8-step process without collision handling — that's slice 6), Content-Type to extension mapping, write to `images/` subfolder. Single attempt only (retry is slice 7).
- Modify: `src/oh_hi_markdown/pipeline.py` — add steps 5, 7, 8 (extract images, download, rewrite) to `run()`. Update RunResult stats.
- Modify: `tests/test_pipeline.py` — remove `@pytest.mark.skip` from T-01. Full pipeline test with 3 mocked images (PNG, JPG, SVG).
- Modify: `tests/test_parser.py` — remove `@pytest.mark.skip` from T-17. Test empty alt text.

**Tests turned green:** T-01, T-17

**Acceptance criteria:** F-1, F-2, P-1, D-1, D-4, D-5, D-9, D-12, R-1, R-2, S-1, S-2, S-3, S-4, L-1 (basic), L-3, O-1, O-2

**Dependencies:** Slice 4

**Done criteria:**
- [ ] T-01 passes: 3 images (PNG, JPG, SVG) mocked, all download, links rewritten to `./images/001-*.png` etc., front matter complete
- [ ] T-17 passes: `![](https://example.com/img.png)` parsed, empty alt preserved in rewrite
- [ ] `images/` subfolder created with all 3 files
- [ ] SVG saved as `.svg` (D-12)
- [ ] `Referer` header set to article URL on image requests (D-9)
- [ ] Image timeout is `(10, 30)` per config
- [ ] `pytest` shows 11 passed, 17 skipped

**Key decisions:**
- Regex uses `re.DOTALL` — critical for multi-line alt text.
- `extract()` filters to http/https URLs only via `urlparse` scheme check. Data URIs, relative paths left untouched.
- `download_all()` creates `images/` subfolder only if ≥1 download succeeds (S-2).
- Image numbering: 001, 002, 003 (3-digit zero-padded). Failed downloads consume their slot.
- `rewrite()` uses `str.replace(original_match, new_match)` — safe because `original_match` is the exact captured text.
- No retry in this slice — if first attempt fails, image is skipped. Retry logic is slice 7.

**Complexity:** L (Large)

---

### Task 6: Slice 6 — Image edge cases

**Scope:** Extend images and parser modules with edge case handling: dedup verification, filename collision disambiguation, query parameter stripping, no-extension URLs, Content-Type validation.

**Files:**
- Modify: `src/oh_hi_markdown/images.py` — add/refine: collision disambiguation (append `-a`, `-b` etc.), query parameter stripping, extension from Content-Type when URL has no extension, Content-Type accept/reject logic per DESIGN.md section 4 table, `image` fallback base name when path produces empty string.
- Modify: `tests/test_images.py` — remove `@pytest.mark.skip` from T-03, T-04, T-05, T-15, T-19, T-26.
- Modify: `tests/test_parser.py` — remove `@pytest.mark.skip` from T-16 (data URI).

**Tests turned green:** T-03, T-04, T-05, T-15, T-16, T-19, T-26

**Acceptance criteria:** D-2, D-13, D-1, D-3, D-14, P-4

**Dependencies:** Slice 5

**Done criteria:**
- [ ] T-03: same URL twice → downloaded once, both refs point to same file
- [ ] T-04: URL `https://cdn.example.com/abc123` with Content-Type `image/png` → saved as `001-abc123.png`
- [ ] T-05: URL `https://example.com/photo.jpg?w=800&q=85` → filename `001-photo.jpg` (query stripped)
- [ ] T-15: two URLs sanitizing to same filename → second gets `-a` suffix
- [ ] T-16: `data:image/png;base64,...` → not extracted, not counted, left untouched
- [ ] T-19: URL returns `Content-Type: text/html` → rejected, no file written, original URL preserved
- [ ] T-26: URL with `.jpg` but no Content-Type → accepted. No extension and no Content-Type → rejected
- [ ] `pytest` shows 18 passed, 10 skipped

**Key decisions:**
- Collision disambiguation: after constructing `{NNN}-{name}.{ext}`, check against all assigned filenames in batch. If collision, try `{NNN}-{name}-a.{ext}`, then `-b`, etc.
- Content-Type validation is strict: non-`image/*` rejected immediately (no retry). Missing Content-Type with known URL extension accepted. Missing Content-Type with no extension rejected.
- Dedup check happens before downloading: if URL already seen, skip download, reuse `ImageDownload` entry.

**Complexity:** M (Medium)

---

### Task 7: Slice 7 — Retry, timeout, redirect, and failure handling

**Scope:** Add retry logic with exponential backoff to image downloads, redirect hop limiting, and graceful all-images-fail handling.

**Files:**
- Modify: `src/oh_hi_markdown/images.py` — wrap single-image download in retry loop: up to 3 retries (4 total attempts), backoff from `config.BACKOFF_DELAYS` (1s, 2s, 4s). Add max redirects (5 hops) via `requests.Session` with `max_redirects` attribute. Handle `TooManyRedirects`. Handle all-images-fail (return empty dict, pipeline creates no `images/` folder).
- Modify: `tests/test_images_retry.py` — remove `@pytest.mark.skip` from T-06, T-07, T-23.

**Tests turned green:** T-06, T-07, T-23

**Acceptance criteria:** D-6, D-7, D-8, R-3, S-2 (all fail), O-1, O-2

**Dependencies:** Slice 5

**Done criteria:**
- [ ] T-06: image 404 → 4 total attempts (verify via `responses` call count), skipped, original URL preserved, outcome "Partial success", exit 0, number slot consumed
- [ ] T-07: all images fail → `article.md` with original URLs, no `images/` folder, outcome "Partial success"
- [ ] T-23: 6 sequential redirects → `TooManyRedirects` → treated as failure, URL preserved
- [ ] Tests patch `BACKOFF_DELAYS` to `(0, 0, 0)` or `time.sleep` to avoid slow tests
- [ ] Retry only for network/HTTP errors, NOT for Content-Type rejection (immediate failure)
- [ ] `pytest` shows 21 passed, 7 skipped

**Key decisions:**
- `requests` does not directly support `max_redirects` on `get()`. Use `Session().max_redirects = 5`.
- Content-Type rejection is not retried — it's a definitive signal, not a transient failure.
- Backoff delays from `config.BACKOFF_DELAYS` — tests must patch these to `(0, 0, 0)`.

**Complexity:** M (Medium)

---

## Chunk 3: Filesystem Safety (Slices 8–10)

### Task 8: Slice 8 — Temp directory assembly + atomic publish

**Scope:** Harden publisher's temp directory and rename flow. Test failure scenario: if `os.rename` fails, no final output folder exists.

**Files:**
- Modify: `src/oh_hi_markdown/publisher.py` — refine `publish()` to handle `OSError` from rename gracefully, raising `FilesystemError` with descriptive message. Ensure `.ohmd-marker` written at temp dir creation.
- Modify: `tests/test_publisher.py` — remove `@pytest.mark.skip` from T-18.

**Tests turned green:** T-18

**Acceptance criteria:** S-4 (atomic write failure safety)

**Dependencies:** Slice 4

**Done criteria:**
- [ ] T-18: patch `os.rename` to raise `OSError` → `FilesystemError` raised, final path does not exist, temp dir with files still exists
- [ ] Test creates real files in temp dir before patching rename
- [ ] `pytest` shows 22 passed, 6 skipped

**Key decisions:**
- On rename failure, publisher raises `FilesystemError` but does NOT delete temp dir — user or stale cleanup handles it.
- Test uses `tmp_path` with pre-created temp dir contents.

**Complexity:** S (Small)

---

### Task 9: Slice 9 — `--force` and conflict handling with rollback

**Scope:** Implement `--force` safe replacement: backup existing → rename temp to final → delete backup (or restore on failure). Implement pre-flight conflict check exit.

**Files:**
- Modify: `src/oh_hi_markdown/publisher.py` — implement `publish_with_force(temp_dir, final_path)`: backup rename (`{folder}.ohmd-backup-{uuid}`), temp-to-final rename, backup delete, rollback on failure. Update `check_conflict()` error message to suggest `--force`.
- Modify: `src/oh_hi_markdown/pipeline.py` — ensure `check_conflict` is called before temp dir creation (verify from slice 4).
- Modify: `tests/test_publisher.py` — remove `@pytest.mark.skip` from T-08, T-09, T-20. Note: T-08 and T-20 depend on pipeline-level behavior but remain in `test_publisher.py` (where they were stubbed). They import and call `pipeline.run()` directly with a mock provider to test the integrated conflict/rollback flow.

**Tests turned green:** T-08, T-09, T-20

**Acceptance criteria:** S-5, S-6

**Dependencies:** Slice 8

**Done criteria:**
- [ ] T-08: folder exists, no `--force` → exit code 3, existing folder untouched, no temp dir created, no HTTP requests (verify via `len(responses.calls) == 0`)
- [ ] T-09: folder exists, `--force` → old folder replaced with new content
- [ ] T-20: folder exists, `--force`, provider raises error → old folder intact (critical rollback test)
- [ ] T-08 asserts stderr contains error message suggesting `--force` (gap O-3)
- [ ] `pytest` shows 25 passed, 3 skipped

**Key decisions:**
- `--force` sequence per DESIGN.md: (1) build in temp, (2) rename existing to backup, (3) rename temp to final, (4) delete backup. If step 3 fails: restore backup, leave temp, raise `FilesystemError`.
- T-20 tests a different scenario: provider fails during run, so we never reach publish step. Existing folder survives because it was never touched.
- T-08 and T-20 test pipeline-level behavior (pre-flight check sequencing, provider failure mid-run) but stay in `test_publisher.py` per the test strategy's module grouping. They call `pipeline.run()` with a mock provider to exercise the full flow.

**Complexity:** M (Medium)

---

### Task 10: Slice 10 — Stale temp cleanup

**Scope:** Implement stale temp directory cleanup at pipeline startup.

**Files:**
- Modify: `src/oh_hi_markdown/publisher.py` — implement `cleanup_stale_temps(parent_dir)`: scan for `.ohmd-tmp-*` dirs, check for `.ohmd-marker`, check age > 10 minutes, delete if both conditions met.
- Modify: `src/oh_hi_markdown/pipeline.py` — call `cleanup_stale_temps()` at start of `run()` (step 1 per DESIGN.md).
- Modify: `tests/test_publisher.py` — remove `@pytest.mark.skip` from T-21.

**Tests turned green:** T-21

**Acceptance criteria:** Stale temp cleanup safety

**Dependencies:** Slice 8

**Done criteria:**
- [ ] T-21: `.ohmd-tmp-xxx` with marker < 10 min old → NOT deleted. `.ohmd-tmp-yyy` with marker > 10 min old → deleted.
- [ ] Directories without `.ohmd-marker` never deleted (even if name matches)
- [ ] Cleanup called before pre-flight conflict check
- [ ] Individual cleanup errors caught — one failure doesn't block others or fail the run
- [ ] Tests use `os.utime()` to set marker mtime
- [ ] `pytest` shows 26 passed, 2 skipped

**Key decisions:**
- Age check uses marker file mtime (not dir mtime — dir mtime changes when contents change).
- Cleanup errors caught per-directory — one failing doesn't stop others.

**Complexity:** S (Small)

---

## Chunk 4: Polish (Slices 11–13)

### Task 11: Slice 11 — Logging + resource warnings

**Scope:** Full logging module: console formatter with `✓`/`⚠` symbols, redaction filter, resource warnings. Enhance log calls throughout codebase.

**Files:**
- Modify: `src/oh_hi_markdown/log.py` — implement `OhmdConsoleFormatter` (custom formatter with `✓`/`⚠`, encoding detection for Windows fallback to `[OK]`/`[WARN]`), `RedactionFilter` (scrubs `Authorization` headers and Bearer tokens), `setup_logging(temp_dir)` with dual handlers (console + file).
- Modify: `src/oh_hi_markdown/images.py` — add resource warning emissions: single image > 10MB, total > 50MB, image count > 50.
- Modify: `src/oh_hi_markdown/pipeline.py` — add summary logging (fetch status, outcome line).
- Modify: `src/oh_hi_markdown/jina.py` — add request/response logging.
- Modify: `src/oh_hi_markdown/publisher.py` — add cleanup and publish logging.

**Tests turned green:** None (no dedicated T-xx tests)

**Acceptance criteria:** L-1, L-2, L-3, L-4, D-10, D-11

**Dependencies:** Slice 4

**Done criteria (inspection-based):**
- [ ] Console output shows: fetch status, per-image `✓`/`⚠` result, summary with outcome/counts
- [ ] `ohmd.log` contains: HTTP status codes, response times, file sizes, URL-to-filename mappings, retry attempts
- [ ] Redaction: set `JINA_API_KEY=test-secret`, verify `ohmd.log` does NOT contain `test-secret`
- [ ] Resource warnings: >50 image refs → warning emitted. 11MB image → warning emitted
- [ ] Windows fallback: mock `sys.stderr.encoding` as `cp1252` → `[OK]`/`[WARN]` used instead of `✓`/`⚠`
- [ ] All previously passing tests still pass (logging changes must not break existing assertions)

**Key decisions:**
- `RedactionFilter` is a `logging.Filter` subclass scanning for `Bearer ...` and `Authorization: ...` patterns.
- Resource thresholds from `config.py` constants (already defined).
- Console formatter: `✓` for INFO, `⚠` for WARNING. Log file uses standard verbose format with timestamps.
- File handler attached at step 6 (temp dir creation). Steps 1-5 log to console only.

**Complexity:** M (Medium)

---

### Task 12: Slice 12 — Alias equivalence

**Scope:** Verify both `ohmd` and `ohhimark` entry points work identically.

**Files:**
- Modify: `tests/test_cli.py` — remove `@pytest.mark.skip` from T-28, implement.

**Tests turned green:** T-28

**Acceptance criteria:** Packaging / entry point verification

**Dependencies:** Slice 1

**Done criteria:**
- [ ] T-28: both `ohmd --version` and `ohhimark --version` produce identical output
- [ ] Both entry points resolve to same `main()` function
- [ ] `pytest` shows 27 passed, 1 skipped

**Key decisions:**
- Test approach: use `importlib.metadata.entry_points()` to verify both map to same callable, plus `subprocess.run` for both `--version` commands.

**Complexity:** S (Small)

---

### Task 13: Slice 13 — Regex edge cases (parentheses in URLs)

**Scope:** Document and test known regex limitation with parenthesized URLs. Verify best-effort behavior.

**Files:**
- Modify: `tests/test_parser.py` — remove `@pytest.mark.skip` from T-22, implement.
- Modify: `src/oh_hi_markdown/parser.py` — no changes expected (regex is intentionally limited per ADR-01). If test reveals partial mangling, add defensive handling.

**Tests turned green:** T-22

**Acceptance criteria:** P-1 (best-effort)

**Dependencies:** Slice 5

**Done criteria:**
- [ ] T-22: `![Wiki image](https://en.wikipedia.org/wiki/File:Example_(test).jpg)` → either correctly extracted (unlikely) or left completely unmodified
- [ ] No partial mangling — output contains either correctly rewritten ref or exact original text
- [ ] All 28 tests pass: 28 passed, 0 skipped

**Key decisions:**
- The regex `([^)]+)` stops at first `)`. For URLs with parens, it captures incorrectly. The test verifies the original text is left untouched.
- This is a documentation test — it records known behavior, not a bug to fix.

**Complexity:** S (Small)

---

## Summary

| Slice | Scope | Tests | Deps | Size | Chunk |
|-------|-------|-------|------|------|-------|
| 1 | CLI + URL validation | T-10, T-24 | — | S | 1 |
| 2 | Provider + Jina | T-11, T-12, T-27 | — | M | 1 |
| 3 | Writer + front matter | T-13, T-14, T-25 | S2 | M | 1 |
| 4 | No-image happy path | T-02 | S1,2,3 | L | 1 |
| 5 | Parser + images | T-01, T-17 | S4 | L | 2 |
| 6 | Image edge cases | T-03,T-04,T-05,T-15,T-16,T-19,T-26 | S5 | M | 2 |
| 7 | Retry + failure | T-06, T-07, T-23 | S5 | M | 2 |
| 8 | Atomic publish | T-18 | S4 | S | 3 |
| 9 | --force + rollback | T-08, T-09, T-20 | S8 | M | 3 |
| 10 | Stale cleanup | T-21 | S8 | S | 3 |
| 11 | Logging | (inspection) | S4 | M | 4 |
| 12 | Aliases | T-28 | S1 | S | 4 |
| 13 | Regex edges | T-22 | S5 | S | 4 |

**Total: 28 tests.** After all 13 slices: 28 passed, 0 skipped.

**Test ID coverage check:** T-01, T-02, T-03, T-04, T-05, T-06, T-07, T-08, T-09, T-10, T-11, T-12, T-13, T-14, T-15, T-16, T-17, T-18, T-19, T-20, T-21, T-22, T-23, T-24, T-25, T-26, T-27, T-28 — all 28 present, each in exactly one slice.
