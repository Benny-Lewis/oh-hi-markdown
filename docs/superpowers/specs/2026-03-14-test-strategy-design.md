# oh-hi-markdown — Test Strategy

**Version:** 1.0
**Date:** 2026-03-14
**Source of truth:** `REQUIREMENTS.md` (locked v1 baseline), `DESIGN.md`

---

## 1. Test Classification by Module

28 unit tests grouped into 9 areas aligned with the module boundaries from `DESIGN.md`.

Tests without formal acceptance criteria IDs (T-10, T-24, T-21, T-28) map to requirements that lack IDs in `REQUIREMENTS.md` — URL validation rules, stale cleanup safety, and CLI entry points. These are shown with parenthetical descriptions in the forward map.

| Area | Module(s) | Tests | What's being verified |
|------|-----------|-------|-----------------------|
| CLI / entry points | `cli` | T-10, T-24, T-28 | URL validation, exit codes, alias equivalence |
| Provider / Jina | `provider`, `jina` | T-11, T-12, T-27 | HTTP errors, rate limiting, empty content |
| Metadata / front matter | `writer` | T-13, T-14, T-25 | Slug generation, title fallback, field order/omission |
| Markdown parsing | `parser` | T-16, T-17, T-22 | Data URIs, empty alt, parenthesized URLs |
| Image download / dedupe | `images` | T-03, T-04, T-05, T-15, T-19, T-26 | Dedup, Content-Type, query params, filename collision, missing headers |
| Retry / error handling | `images` | T-06, T-07, T-23 | Retry backoff, all-fail, redirect limit |
| Temp dir / publish / rollback | `publisher` | T-08, T-09, T-18, T-20, T-21 | Conflict, force, atomic write, rollback, stale cleanup |
| Logging | `log` | (none — cross-cutting) | Redaction filter, dual-handler setup, encoding fallback. Verified via pipeline/image tests (L-1 through L-4) and by inspection during logging module implementation |
| Happy path (end-to-end unit) | `pipeline` | T-01, T-02 | Full pipeline with mocked HTTP — images and no-images |

---

## 2. Fixture Strategy

### HTTP mocking: `responses` library

All HTTP interactions are mocked using the `responses` library (`@responses.activate` decorator). No real network calls in unit tests.

**Provider tests:**
- Register Jina API URL (`https://r.jina.ai/*`) with appropriate status codes and JSON bodies
- T-11: register 500 response
- T-12: register 429 response
- T-27: register 200 with empty `content` field

**Image download tests:**
- Register image URLs with appropriate Content-Type headers and binary payloads
- T-06: use `responses.CallbackResponse` to return 404 on all 4 attempts (1 initial + 3 retries), verifying retry count
- T-23: chain 6 sequential 301 redirects to exceed the 5-hop limit
- T-19: register image URL returning `Content-Type: text/html`
- T-26: register image URL with no `Content-Type` header

**Pipeline tests (T-01, T-02):**
- Mock both the Jina API endpoint and all image URLs to run the full pipeline without network access

### Filesystem: `tmp_path` + selective patching

All tests that produce filesystem output use pytest's built-in `tmp_path` fixture. Real filesystem operations for happy paths; targeted `unittest.mock.patch` for failure scenarios.

**Real filesystem:**
- T-08, T-09: pre-create directories in `tmp_path` to simulate existing output
- T-21: pre-create stale and fresh `.ohmd-tmp-*` directories with `.ohmd-marker` files
- T-09, T-20: pre-populate existing output folder with known content for replacement verification

**Patched filesystem:**
- T-18: patch `os.rename` to raise `OSError` after images are written to temp dir — verify no final output folder exists
- T-20: patch the provider to raise `ProviderHTTPError` after the pre-flight check passes — verify existing folder survives intact

### Shared fixtures (`conftest.py`)

| Fixture | Contents | Used by |
|---------|----------|---------|
| `sample_fetch_result` | `FetchResult` with title, author, date, description, and markdown containing 3 image references (one PNG, one JPG, one SVG) | T-01, T-02 (no-images variant), T-13, T-14 (overrides title to `None`), T-25 |
| `jina_success_response` | JSON dict matching Jina's `Accept: application/json` response format | Provider and pipeline tests |
| `png_bytes` / `jpg_bytes` / `svg_bytes` | Minimal valid image binaries (1x1 pixel PNGs/JPGs, minimal SVG) | Image download tests |

**Not shared (inline per-test):**
- Error scenario mocks — the `responses` setup is the interesting part of each error test
- Publisher directory structures — the filesystem precondition is what each publisher test verifies

---

## 3. Traceability Map

### Forward map: test -> acceptance criteria

| Test | Criteria covered |
|------|-----------------|
| T-01 | F-1, F-2, P-1, D-1, D-4, D-5, D-9, R-1, R-2, S-1, S-2, S-3, S-4, L-1, L-3, O-1, O-2 |
| T-02 | F-1, S-1, S-2, S-3, O-1, O-2 |
| T-03 | D-2, D-13 |
| T-04 | D-1 |
| T-05 | D-1 |
| T-06 | D-6, D-7, L-1, O-1, O-2 |
| T-07 | D-7, S-1, S-2, R-3, O-1, O-2 |
| T-08 | S-5 |
| T-09 | S-6 |
| T-10 | (URL validation — pre-fetch gate) |
| T-11 | F-4 |
| T-12 | F-5 |
| T-13 | S-1 |
| T-14 | S-1 |
| T-15 | D-3 |
| T-16 | P-4 |
| T-17 | P-1, R-2 |
| T-18 | S-4 |
| T-19 | D-14, R-3 |
| T-20 | S-6 |
| T-21 | (stale temp cleanup safety) |
| T-22 | P-1 (best-effort) |
| T-23 | D-8 |
| T-24 | (URL validation — pre-fetch gate) |
| T-25 | S-3 |
| T-26 | D-14, D-1 |
| T-27 | F-6 |
| T-28 | (packaging / entry point verification) |

### Reverse map: acceptance criteria -> tests

| Criteria | Description | Covered by |
|----------|-------------|-----------|
| F-1 | Valid URL triggers Jina fetch | T-01, T-02 |
| F-2 | `X-With-Generated-Alt: true` header sent | T-01 |
| F-3 | `JINA_API_KEY` included as Bearer token when set | — (see gap resolution) |
| F-4 | Jina HTTP error or unreachable -> exit 2 | T-11 (HTTP error path) |
| F-5 | Jina 429 -> exit 2, suggest API key | T-12 |
| F-6 | Empty/whitespace markdown -> exit 2 | T-27 |
| P-1 | Extract `![alt](url)` references | T-01, T-17, T-22 |
| P-2 | HTML `<img>` tags best-effort | (best-effort, no test required) |
| P-3 | Nested image-links best-effort | (best-effort, no test required) |
| P-4 | Data URIs ignored | T-16 |
| D-1 | Image HTTP GET attempted | T-01, T-04, T-05, T-26 |
| D-2 | Duplicate URL downloaded once | T-03 |
| D-3 | Filename collision disambiguated | T-15 |
| D-4 | Sequential downloads | T-01 |
| D-5 | 30-second image timeout | T-01 |
| D-6 | Retry 3 times with backoff | T-06 |
| D-7 | Failed image skipped, warning logged | T-06, T-07 |
| D-8 | Redirect limit exceeded -> failed | T-23 |
| D-9 | `Referer` header set to article URL | T-01 |
| D-10 | Single image > 10 MB and total download > 50 MB warnings | (verified by inspection during logging module implementation) |
| D-11 | Image count > 50 warning | (verified by inspection during logging module implementation) |
| D-12 | SVG saved as `.svg` | T-01 |
| D-13 | Different URLs, same binary not deduped | T-03 |
| D-14 | Non-`image/*` Content-Type rejected | T-19, T-26 |
| R-1 | Successful images rewritten to `./images/` | T-01 |
| R-2 | Alt text preserved exactly | T-01, T-17 |
| R-3 | Failed images keep original URL | T-07, T-19 |
| S-1 | Output folder + `article.md` + `ohmd.log` always created | T-01, T-02, T-07, T-13, T-14 |
| S-2 | `images/` only if >= 1 image succeeds | T-01, T-02, T-07 |
| S-3 | `article.md` has front matter + markdown | T-01, T-02, T-25 |
| S-4 | Temp dir -> atomic rename | T-18 |
| S-5 | Folder exists, no `--force` -> exit 3 | T-08 |
| S-6 | `--force` safe replacement | T-09, T-20 |
| L-1 | Console output shows fetch/download/summary | T-01, T-06 |
| L-2 | `ohmd.log` has full detail | (verified by inspection during logging module implementation) |
| L-3 | Log file inside output folder | T-01 |
| L-4 | Resource warnings in console and log | (verified by inspection during logging module implementation) |
| O-1 | Exit 0 on success or partial success | T-01, T-02, T-06, T-07 |
| O-2 | Summary with outcome/counts printed | T-01, T-02, T-06, T-07 |
| O-3 | Failure summary prints "Failed" | — (see gap resolution) |

### Gap resolution

| Gap | Resolution |
|-----|-----------|
| F-3 (`JINA_API_KEY` Bearer token) | Add env var assertion to T-11: set `JINA_API_KEY`, verify `Authorization: Bearer` header in `responses` request history |
| F-4 (unreachable provider path) | T-11 covers the HTTP error path. Add a `ProviderUnreachableError` assertion (mock `requests.get` to raise `ConnectionError`) to verify the DNS/connection-timeout path also maps to exit code 2 |
| O-3 (failure summary output) | Add assertion to T-08 and T-11 that captured stderr/stdout contains "Failed" |
| D-10, D-11, L-2, L-4 (resource warnings and log detail) | Verified by inspection during logging module implementation (see `PLAN.md` step 7, slice 11) |

---

## 4. Release Gate

### CI matrix

| | Python 3.10 | Python 3.11 | Python 3.12 |
|---|---|---|---|
| **Ubuntu (latest)** | pytest | pytest | pytest |
| **macOS (latest)** | pytest | pytest | pytest |

6 matrix cells. All 28 unit tests must pass on all 6 cells.

### Additional CI checks

- `ruff check` — linting
- `ruff format --check` — formatting

### Integration tests

I-01 through I-05 are run manually before release, not in CI. They hit real URLs and require network access.

| ID | Scenario |
|----|----------|
| I-01 | Real tech blog post with mixed image types (PNG, JPG, SVG) |
| I-02 | Real news article with hero image and inline photos |
| I-03 | Real documentation page with diagrams and code screenshots |
| I-04 | Article with many images (10+) |
| I-05 | Article where some images are hotlink-protected |

Specific URLs are selected during the manual integration testing phase (see `PLAN.md` step 8). Results are documented with URL, what it exercises, and outcome.

### Release criteria

1. All 28 unit tests pass on all 6 CI matrix cells
2. `ruff check` and `ruff format --check` pass
3. Integration tests I-01 through I-05 run and documented
4. All acceptance criteria covered per traceability map — gap resolution items (F-3, F-4 unreachable path, O-3) must have their planned assertions implemented before release

---

## 5. Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `responses` | HTTP mocking for `requests` |
| `ruff` | Linter and formatter |

No `pytest-cov` (coverage tracked via traceability map, not line-level metrics), `pyfakefs`, or `pytest-httpserver` needed.
