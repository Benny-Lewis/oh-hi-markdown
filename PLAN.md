# oh-hi-markdown — Development Lifecycle Plan

**Last updated:** 2026-03-17

---

### 1. Lock the requirements ✅

- Mark `REQUIREMENTS.md` as the v1 implementation baseline
- Move any remaining ideas or "nice to haves" to the deferred/backlog section
- Stop editing the spec casually — changes from here go through a lightweight change process (noted reason, updated date, reviewed before merging)

**Produces:** Locked `REQUIREMENTS.md`

---

### 2. Write the technical design doc ✅

- Top-level architecture and module boundaries
- Data flow through the pipeline (URL in → folder out)
- Provider interface and Jina provider implementation approach
- Markdown parsing approach (regex pattern, edge case handling)
- Image extraction, deduplication, and download/retry flow
- Filename resolution logic
- Metadata extraction and front matter generation
- Temp directory lifecycle and atomic publish/rollback flow
- `--force` safe-replacement sequence
- Logging model (console output, log file, redaction)
- Config and environment variable handling (`JINA_API_KEY`)
- Error propagation strategy and exit code mapping
- Platform assumptions and known limitations
- Key implementation choices with rationale (e.g., `argparse` vs `click`, `requests` vs `httpx`, regex vs parser library)
- Lightweight ADRs for any decisions that may be revisited later

**Produces:** Technical design doc

---

### 3. Do a quick risk/spike check ✅

- Review the design doc for assumptions that are unproven or high-risk
- Identify whether a short spike is needed before full build

**Recommended spike candidates:**
1. **Parser validation** — run the regex pattern against 5-10 real Jina Reader outputs to confirm `![alt](url)` extraction holds in practice and identify any edge cases in real data
2. **Filesystem publish/rollback** — test the temp-dir → atomic-rename → rollback flow on macOS and Linux to confirm behavior matches spec

**Decision gate:**
- If spikes reveal problems: correct the design doc before proceeding
- If spikes confirm assumptions: document the results briefly and move on

**Produces:** Spike results (if needed), any design corrections, confidence to proceed

---

### 4. Write a short test strategy ✅

- Classify tests by area: provider, metadata/front matter, slug/filename generation, markdown parsing, image download/dedupe, retry/error handling, temp-dir/publish/rollback, CLI/exit codes, packaging/aliases
- Define fixture strategy: what gets mocked, what gets recorded, what hits real URLs
- Define the release gate (all 28 unit tests pass on macOS + Linux, integration tests run manually)
- Build a traceability map: acceptance criteria IDs (F-1, D-7, S-4, etc.) → test case IDs (T-01, T-14, etc.), ensuring every acceptance criterion is covered by at least one test

**Produces:** Test plan with traceability map

---

### 5. Set up project scaffolding ✅

- Create the GitHub repo (`Benny-Lewis/oh-hi-markdown`)
- `pyproject.toml` with package metadata, Python 3.10+ requirement, dependencies, entry points (`ohmd` + `ohhimark`)
- `src/oh_hi_markdown/` package structure matching the design doc's module boundaries
- `LICENSE` (MPL-2.0)
- `.gitignore`
- Formatter/linter config (`ruff`)
- Type checking config (`mypy`) if desired
- `pytest` config
- CI via GitHub Actions: lint + test matrix (Python 3.10/3.11/3.12 × macOS/Linux)
- Verify: `pip install -e .` works, `ohmd --version` prints something, `ohhimark --version` prints the same thing, `pytest` runs and finds tests
- README stub (install instructions, brief description, "work in progress" note)
- Commit `REQUIREMENTS.md` to the repo
- **Stub all 28 named test cases** as empty `test_` functions with docstrings matching the spec IDs and scenarios, marked as `skip` or expected-fail — this gives a built-in progress dashboard from day one

**Produces:** Working repo, CI green on empty project, 28 stubbed tests visible

---

### 6. Plan implementation sequence ✅

- Order the vertical slices by dependency
- Define done criteria for each (which tests turn green)

**Suggested slice order:**

| Slice | Scope | Tests turned green |
|---|---|---|
| 1 | CLI shell + URL validation + exit codes | T-10, T-24 |
| 2 | Provider interface + Jina fetch + error handling | T-11, T-12, T-27 |
| 3 | Metadata extraction + front matter generation + slug/folder naming | T-13, T-14, T-25 |
| 4 | No-image happy path (fetch → front matter → write article.md → publish) | T-02 |
| 5 | Markdown image parsing + basic image download + link rewriting | T-01, T-17 |
| 6 | Image edge cases: dedup, filename collision, query params, no extension, Content-Type validation | T-03, T-04, T-05, T-15, T-16, T-19, T-26 |
| 7 | Retry, timeout, redirect, and failure handling | T-06, T-07, T-23 |
| 8 | Temp directory assembly + atomic publish | T-18 |
| 9 | `--force` and conflict handling with rollback | T-08, T-09, T-20 |
| 10 | Stale temp cleanup | T-21 |
| 11 | Logging (console output, log file, redaction) + resource warnings | (verified by inspection + existing tests) |
| 12 | Alias equivalence | T-28 |
| 13 | Regex edge cases (parentheses in URLs, etc.) | T-22 |

**Produces:** Ordered implementation plan with per-slice done criteria

---

### 7. Implement in vertical slices ✅

- Build in slice order from step 6
- Each slice: write code → turn the targeted tests green → commit
- Verify continuously against the test plan
- If a design assumption breaks during implementation, feed it back through the design doc before patching around it
- Do not skip ahead to later slices while earlier slice tests are still red

**Completed:** All 13 slices implemented, 29 tests passing, lint clean. Merged via PR #5.

---

### 8. Run manual integration tests ✅

- Execute I-01 through I-05 against real URLs
- Select specific URLs during this phase based on real-world testing
- Document each URL, what it exercises, and the result
- Fix any issues found, update tests if new edge cases emerge
- Add any new test cases discovered during integration testing

**Produces:** Integration test results, any bug fixes, updated test suite

**Results (2026-03-17):** All 5 integration tests passed (451 images across 5 articles). Two bugs found and fixed: (1) `X-With-Generated-Alt` header requires API key — now conditional; (2) `application/octet-stream` Content-Type rejected — now falls back to URL extension. See `docs/integration-test-results.md` for full details. PR #6.

---

### 9. Finish docs

- Flesh out README: install instructions, usage examples, environment variable setup, known limitations, link to `REQUIREMENTS.md`
- Clean up `--help` output to match the CLI spec exactly
- Document the `Referer` header behavior and Jina data submission as noted in the spec
- Add a CONTRIBUTING.md if desired for an open source project

**Produces:** Complete user-facing documentation

---

### 10. Tag release

- Confirm all 32 unit tests pass on macOS and Linux (CI green)
- Confirm integration tests have been run and documented
- Confirm README and `--help` are complete
- Tag `v0.1.0`
- Publish: `pip install git+https://github.com/Benny-Lewis/oh-hi-markdown`
- Capture any post-release findings into a v0.2 backlog

**Produces:** Tagged release, published package, v0.2 backlog
