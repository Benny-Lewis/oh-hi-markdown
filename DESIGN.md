# oh-hi-markdown — Technical Design Document

**Version:** 1.2
**Last updated:** 2026-03-17
**Status:** Complete — all sections drafted
**Source of truth:** `REQUIREMENTS.md` (locked v1 baseline)

---

## 1. Architecture Overview

The tool is organized as a linear pipeline of eight modules. Data flows from URL input through fetch, parse, download, and write stages, ending with atomic publish to the final output path.

```
cli
 │  parses args, validates URL
 │  calls pipeline.run(url, options)
 │
 ▼
pipeline.run()
 │
 ├─1─▶ provider.fetch(url) ──▶ FetchResult
 │
 ├─2─▶ parser.extract(markdown) ──▶ list[ImageRef]
 │
 ├─3─▶ images.download_all(image_refs, article_url, temp_dir) ──▶ dict[url → ImageDownload]
 │
 ├─4─▶ parser.rewrite(markdown, image_refs, url_map) ──▶ rewritten markdown
 │
 ├─5─▶ writer.assemble(fetch_result, rewritten_markdown, temp_dir) ──▶ writes article.md into temp_dir
 │
 ├─6─▶ publisher.publish(temp_dir, final_path, force=bool) ──▶ atomic rename
 │
 └────▶ return RunResult(outcome, stats)

cli
 │  maps RunResult or exceptions to exit code + console summary
 ▼
sys.exit()
```

### Module boundaries

| Module | Responsibility |
|--------|---------------|
| `cli` | Argparse, entry points (`ohmd` / `ohhimark`), URL validation, maps exceptions to exit codes, calls `pipeline.run()` |
| `pipeline` | Orchestrates the full sequence — calls modules in order, owns the "what happens in what order" logic |
| `provider` (protocol) | Defines the `ContentProvider` protocol and `FetchResult` dataclass — the contract any content provider must fulfill |
| `jina` (implementation) | Jina-specific HTTP logic: URL construction, headers, API key, response parsing, error detection |
| `parser` | Extracts `![alt](url)` image references from markdown via regex; rewrites image URLs after download |
| `images` | Downloads images: deduplication, retry/backoff, Content-Type validation, filename resolution, resource warnings |
| `writer` | Front matter generation (title fallback chain, slug, date normalization, field ordering), `article.md` assembly |
| `publisher` | Temp directory lifecycle, atomic rename, `--force` backup/restore/rollback, stale temp cleanup |
| `log` | Dual-output logging setup (console with `✓`/`⚠` formatting + `ohmd.log` file), redaction filter for secrets |

### Key design decisions

**Orchestration lives in a dedicated `pipeline` module**, not in `cli`. This allows testing the full pipeline with a simple function call without dealing with argparse or sys.exit.

**The parser owns both extraction and rewriting**, since it's the module that understands markdown image syntax. The writer receives finished markdown and doesn't need to know about image syntax.

**The writer is separate from the publisher** despite both touching the temp directory. The writer handles *content* (what goes in `article.md`), the publisher handles *filesystem safety* (atomic rename, rollback).

**Logging is cross-cutting**, not a pipeline step. The `log` module configures handlers at setup; every other module uses the standard logger.

---

## 2. Provider Interface and Jina Implementation

### Provider protocol

The content-fetching layer is behind an internal provider interface, allowing the Jina dependency to be swapped for alternatives (percollate, self-hosted Jina, readability-cli + pandoc) without rewriting the image pipeline.

```python
class ContentProvider(Protocol):
    def fetch(self, url: str) -> FetchResult: ...
```

### FetchResult dataclass

```python
@dataclass
class FetchResult:
    markdown: str           # The article content as markdown
    title: str | None       # Article title
    author: str | None      # Article author (normalized at provider layer)
    date: str | None        # Article publication date (normalized at provider layer)
    description: str | None # Article description / summary
    source_url: str         # The original URL
```

**Design rationale:** This matches the locked `FetchResult` contract in `REQUIREMENTS.md`. The provider is responsible for normalizing `author` and `date` before returning — downstream modules never touch provider-specific metadata. This keeps the pluggable provider boundary clean: any provider that can extract author/date returns them directly; the writer and pipeline are provider-agnostic.

**Deviation from REQUIREMENTS.md:** The spec's `FetchResult` has no canonical URL field. The Jina implementation stores the canonical URL (which may differ from the input) internally for logging but does not expose it via `FetchResult`. If needed in the future, `url: str | None` can be added to the contract.

### Jina Reader API: request construction

**URL:** `https://r.jina.ai/{original_url}` (user's URL appended directly)

**Headers:**

| Header | Value | Condition |
|--------|-------|-----------|
| `Accept` | `application/json` | Always — returns structured JSON with metadata |
| `X-With-Generated-Alt` | `true` | Only when `JINA_API_KEY` is set — Jina requires auth for AI image captions |
| `User-Agent` | `ohmd/{version}` | Always — consistent with image requests |
| `Authorization` | `Bearer {key}` | Only if `JINA_API_KEY` env var is set |

**Timeouts:** `(10, 60)` — 10-second connection timeout, 60-second read timeout (per spec).

### Jina Reader API: response handling

The Jina JSON response structure (with `Accept: application/json`):

```json
{
  "code": 200,
  "status": 20000,
  "data": {
    "title": "...",
    "description": "...",
    "url": "...",
    "content": "... (the markdown) ...",
    "publishedTime": "...",
    "metadata": {
      "lang": "en",
      "og:image": "...",
      "og:title": "...",
      ...
    },
    "usage": { "tokens": 29 }
  }
}
```

On success: parse JSON, extract fields from `data`, pack into `FetchResult`. Validate that `data.content` is non-empty and non-whitespace.

### Jina Reader API: error handling

Five distinct failure modes, all mapping to exit code 2 but with different user-facing messages. Implemented as an exception hierarchy:

```python
class ProviderError(Exception):
    """Base class for provider failures."""
    ...

class ProviderHTTPError(ProviderError):
    """Jina returned 4xx/5xx (not 429). Carries status_code."""
    ...

class ProviderRateLimitError(ProviderError):
    """Jina returned 429. Message suggests setting JINA_API_KEY."""
    ...

class ProviderEmptyContentError(ProviderError):
    """Jina returned HTTP 200 but content is empty/whitespace."""
    ...

class ProviderUnreachableError(ProviderError):
    """Jina host is unreachable (DNS failure, connection refused, network timeout)."""
    ...

class ProviderDecodeError(ProviderError):
    """Jina returned a response that cannot be decoded as text."""
    ...
```

**Rationale for multiple exception classes over a single exception with reason enum:** The five failure modes carry different data (HTTP error has a status code, rate limit may carry retry-after info in the future, unreachable carries the underlying connection error, decode error carries encoding details, empty content has neither). Separate classes let each carry exactly what it needs. It's also the most Pythonic pattern — the pipeline can catch each separately, and adding new handling (e.g., automatic retry for rate limits in v2) is a matter of extending one catch block.

### Deferred to v2

The following Jina headers are noted as v2 candidates:

| Header | Purpose |
|--------|---------|
| `X-No-Cache: true` | Bypass Jina's page cache (~3600s). Potential `--no-cache` CLI flag. |
| `X-Wait-For-Selector` | Wait for a specific CSS element before extracting. |
| `X-Target-Selector` | Focus extraction on a specific page element. |
| `X-Timeout` | Custom page-load timeout for slow/dynamic pages. |
| `Accept: text/event-stream` | Streaming mode — more reliable for pages with lazy-loaded content. |

---

## 3. Parser Module

The parser is the only module that understands markdown image syntax. It has two responsibilities: finding image references, and rewriting their URLs after download.

### Data structure

```python
@dataclass
class ImageRef:
    alt: str            # the alt text (may be empty, may be multi-line)
    url: str            # the image URL
    original_match: str # the full matched text, e.g. "![alt](url)"
```

The `original_match` field enables safe find-and-replace during rewriting — we search for the exact original string rather than reconstructing it from parts, avoiding subtle whitespace or formatting mismatches.

### Regex pattern

```python
IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\(([^)]+)\)', re.DOTALL)
```

- `(.*?)` captures alt text — any characters including newlines (non-greedy). `re.DOTALL` is **required** here because Python's `.` does not match `\n` by default. Without it, `.*?` would fail to match multi-line alt text, which the requirements explicitly support.
- `([^)]+)` captures the URL — anything except `)`.

**Known limitation (T-22):** URLs containing literal parentheses (e.g., Wikipedia URLs) will not parse correctly. This is documented as best-effort per the spec. If the regex fails to extract such an image, the reference is left completely unmodified in the output.

### Methods

**`extract(markdown: str) -> list[ImageRef]`**

- Scans markdown with the regex pattern
- For each match, checks if the URL uses `http://` or `https://` scheme — only these are considered downloadable per the locked requirements. All other schemes (`data:`, `file://`, `mailto:`, relative paths, etc.) are skipped and left unmodified in output.
- Creates an `ImageRef` for each valid match
- Returns the list in parse order (top to bottom of markdown)

**`rewrite(markdown: str, image_refs: list[ImageRef], url_map: dict[str, str]) -> str`**

- Takes the original markdown, the list of `ImageRef` objects from extraction, and a dictionary mapping original URLs to local filenames
- For each `ImageRef` whose URL appears in `url_map`, replaces that specific `original_match` string with `![{alt}](./images/{local_filename})`, preserving the exact alt text from the original reference
- This approach correctly handles the case where the same image URL appears multiple times with different alt text — each `original_match` is unique and replaced independently
- URLs not in `url_map` (failed downloads) are left untouched

---

## 4. Images Module

This is the meatiest module in the tool. It handles the full image download lifecycle.

### Interface

```python
@dataclass
class ImageDownload:
    filename: str   # e.g., "002-diagram.png"
    size: int       # bytes, for logging and resource warnings

def download_all(
    image_refs: list[ImageRef],
    article_url: str,
    temp_dir: Path
) -> dict[str, ImageDownload]:
    """Returns dict mapping original URL -> ImageDownload for successes only.
    Failed URLs are absent from the dict."""
```

### Deduplication and numbering

Before any downloads, the module scans `image_refs` in order and builds an ordered mapping of unique URLs:

- Each unique URL (first occurrence) gets a sequential number: 001, 002, 003...
- Duplicate URLs (later occurrences) reuse the first occurrence's number and filename
- Numbers are assigned before downloading — **failed downloads consume their number slot** (if 002 fails, the next image is 003). This keeps numbering stable across re-runs.

### Per-image download flow

For each unique URL:

1. **HTTP GET request** with:
   - `User-Agent: ohmd/{version}`
   - `Referer: {article_url}` (for hotlink-protected images)
   - Timeout: `(10, 30)` — 10s connect, 30s read
   - Max 5 redirect hops

2. **Content-Type validation** (see below). If Content-Type is invalid, fail immediately — no retry.

3. **On failure** (network error, timeout, HTTP error status, redirect limit exceeded): retry up to 3 times with exponential backoff (1s, 2s, 4s delays before each retry).

4. **After 4 total attempts fail:** skip the image, log a warning, print a console warning, move to the next image.

### Content-Type validation

After a successful HTTP response (status 200), the Content-Type determines acceptance:

| Scenario | Action |
|----------|--------|
| Content-Type present, starts with `image/` | **Accept.** Use Content-Type to determine file extension. |
| Content-Type is `application/octet-stream`, URL has known image extension | **Accept.** Use the URL extension. Common on GCS and similar CDNs, especially for WebP. |
| Content-Type is `application/octet-stream`, URL has no known image extension | **Reject.** |
| Content-Type present, NOT `image/*` and NOT `application/octet-stream` | **Reject immediately.** No retry. Catches HTML error pages, anti-hotlink redirects, CDN errors. |
| Content-Type missing, URL has known image extension (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.avif`, `.bmp`, `.tiff`) | **Accept.** Use the URL extension. |
| Content-Type missing, URL has no recognizable image extension | **Reject.** |
| Content-Type is `image/*` but unknown subtype, URL has extension | **Accept.** Use URL extension. |
| Content-Type is `image/*` but unknown subtype, no URL extension | **Accept.** Use `.bin`. |

### Content-Type to extension mapping

| Content-Type | Extension |
|-------------|-----------|
| `image/png` | `.png` |
| `image/jpeg` | `.jpg` |
| `image/gif` | `.gif` |
| `image/webp` | `.webp` |
| `image/svg+xml` | `.svg` |
| `image/avif` | `.avif` |
| `image/bmp` | `.bmp` |
| `image/tiff` | `.tiff` |

### Filename resolution

Eight-step process for each image:

1. **Extract filename from URL path** — everything after the last `/`, before any `?`.
2. **URL-decode** the filename.
3. **Sanitize** — replace characters not in `[a-zA-Z0-9._-]` with `-`.
4. **Collapse consecutive hyphens** and **strip leading/trailing hyphens** from the base name.
5. **If empty**, use `image` as the base name.
6. **Determine extension** — prefer Content-Type mapping, fall back to URL extension. `.bin` only for confirmed `image/*` with no known mapping and no URL extension.
7. **Prepend sequence number** — `{NNN}-{sanitized-name}.{ext}`.
8. **Collision check** — if another image in the batch already produced the same filename, append `-a`, `-b`, etc. before the extension.

### Resource warnings

Emitted via the standard logger (routed to both console and log file):

| Threshold | Trigger | Frequency |
|-----------|---------|-----------|
| Single image > 10 MB | After saving that image | Per-image |
| Total download size > 50 MB | When running total crosses threshold | Once |
| More than 50 images found | After deduplication, before downloading | Once |

Warnings do not stop the download — they are informational only.

---

## 5. Writer Module

The writer handles content assembly: generating front matter, creating the output folder slug, and writing `article.md` to the temp directory.

### Slug generation and title fallback chain

The slug (used as the output folder name) and the front matter `title` are produced together by a single fallback chain. The slug is always ASCII-safe; the title preserves the original text. Both live in the writer module because they're tightly coupled — two outputs of the same logic.

| Priority | Condition | Slug | Front matter `title` |
|----------|-----------|------|---------------------|
| 1 | Jina returns a title and slugifying it produces a non-empty slug | Slugify the title | The Jina title |
| 2 | Priority 1 slug is empty, but title contains transliterable non-ASCII characters | Transliterate (e.g., `ü` → `u`, `é` → `e`), then slugify | The original (non-transliterated) Jina title |
| 3 | No usable title from Jina, but markdown has an H1 heading | Slugify the H1 text (with transliteration if needed, as in priority 2) | The H1 text |
| 4 | No title, no H1, but URL has a meaningful path (more than just `/`) | Slugify the URL path component | Domain + path (e.g., `"example.com/some-article"`) |
| 5 | All above produce an empty slug | Timestamp: `article-YYYYMMDD-HHMMSS` | The full URL |

**Slugification rules:** Lowercase, replace spaces with hyphens, strip characters not in `[a-z0-9-]`, collapse consecutive hyphens, strip leading/trailing hyphens, truncate to 80 characters at a word boundary. Transliteration for non-ASCII characters (e.g., `ü` → `u`, `é` → `e`) via `unicodedata` or a small library.

The pipeline calls `writer.generate_slug(fetch_result)` to get the slug for determining the final output path, before the writer assembles the full file.

### Author handling

The writer receives `FetchResult.author` directly — author extraction from provider-specific metadata is the provider's responsibility, not the writer's. If `author` is `None`, the field is omitted from front matter entirely. If the value is a URL (some pages put author profile URLs in meta tags), it's used as-is in v1 — resolving URLs to names is a v2 concern.

**Jina provider's author extraction:** The Jina implementation normalizes author before returning `FetchResult` by checking page metadata keys in priority order: `author`, `article:author`, `og:author`, `citation_author`. First non-empty value wins.

### Date normalization

The writer receives `FetchResult.date` already extracted by the provider. It uses `python-dateutil` (added as a dependency) to normalize the date string into ISO 8601 format (`YYYY-MM-DD`). If parsing fails, the original string is included as-is in front matter and a warning is logged. If `date` is `None`, the field is omitted from front matter.

**Jina provider's date extraction:** The Jina implementation normalizes date before returning `FetchResult` by checking `data.publishedTime` first. If absent, it falls back to page metadata keys: `article:published_time`, `date`, `DC.date`. First non-empty value wins. This ensures front matter completeness even when the top-level `publishedTime` field is empty.

This handles the variety of date formats Jina returns (e.g., `"Wed, 11 Mar 2026 19:06:45 GMT"`, `"2003-04-16T13:12:08Z"`) without writing custom parsers.

### Front matter serialization

Fields appear in fixed order, all values as quoted strings, optional fields omitted if empty:

1. `title` (required)
2. `author` (if present)
3. `date` (if present)
4. `source_url` (required)
5. `description` (if present)
6. `downloaded` (required — ISO 8601 with timezone: `"YYYY-MM-DDTHH:MM:SSZ"`)
7. `tool` (required — `"ohmd v0.1.0"`)

**Implementation:** Manual string building rather than `pyyaml` dump. This guarantees deterministic field ordering, consistent quoting, and exact match with the spec. A small escape function handles special characters in values (double quotes, backslashes). See ADR-02 for rationale.

### Assembly

The writer concatenates `---\n`, front matter fields, `---\n`, a blank line, and the rewritten markdown, then writes the result to `article.md` in the temp directory.

---

## 6. Publisher Module

The publisher handles filesystem safety: promoting the temp directory to the final output path, safe replacement with `--force`, and cleanup of stale temp directories.

### Atomic publish (normal path)

All output is written to a temp directory named `.ohmd-tmp-{uuid}` inside the output parent directory. The temp directory contains a `.ohmd-marker` file (written immediately on creation), `article.md`, `ohmd.log`, and optionally `images/`.

**Pre-flight check:** Before any temp artifacts are created, the pipeline calls `publisher.check_conflict(final_path, force)`. If the path exists and `--force` is not set, this raises `FilesystemError` immediately (exit code 3). This ensures no temp directories, log files, or downloads are created for a run that would fail anyway — per S-5 ("No files shall be modified").

Once all files are written and closed:

1. Rename the temp directory to the final output path. On macOS and Linux (same filesystem), this is atomic — it either completes fully or doesn't happen.
2. If the rename fails (permissions, cross-filesystem, etc.), the temp directory stays in place and we exit with code 3. No partial output at the final path.

### `--force` safe replacement

When `--force` is passed and the output folder already exists, the goal is to never leave the user with *nothing*. The sequence:

1. New output is fully built in the temp directory (same as normal path — existing folder is untouched up to this point).
2. Rename the existing folder to a backup: `{folder}.ohmd-backup-{uuid}`.
3. Rename the temp directory to the final output path.
4. If step 3 succeeds: delete the backup folder. Done.
5. If step 3 fails: restore the backup to the original name, leave the temp directory in place, exit with code 3. The user's original output is preserved.

**Critical property:** Step 2 only happens after the new output is fully complete. If the new run fails at *any* point before step 2 (fetch error, image download failure, write error), the existing folder is never touched. The user either gets the new output or keeps the old output — never nothing.

**Edge case:** If the backup rename in step 2 fails, we haven't touched the original folder — exit with code 3 and leave the temp directory in place.

### Stale temp cleanup

On startup, before any other work, the publisher scans the output parent directory for leftover `.ohmd-tmp-*` directories from previous crashed or interrupted runs.

**Safety rules:**

1. **Only delete directories containing a `.ohmd-marker` file.** Prevents accidentally deleting unrelated directories that happen to match the naming pattern.
2. **Only delete directories whose marker file was last modified more than 10 minutes ago.** Prevents one invocation from deleting another invocation's active temp directory during concurrent runs.

Each cleanup action is logged to the console (stderr). If the run later succeeds, the cleanup summary is also included in `ohmd.log`. At the time of cleanup, the log file doesn't exist yet (no output folder), so cleanup messages go to console only.

---

## 7. CLI Module

The CLI is the entry point — argument parsing, URL validation, and exit code mapping. It is the only module that calls `sys.exit()`.

### Argument parsing

Uses `argparse` with the interface defined in the spec:

```
usage: ohmd [-h] [-o OUTPUT] [--force] [--version] url
       ohhimark [-h] [-o OUTPUT] [--force] [--version] url

Note: URLs are sent to Jina Reader (r.jina.ai) for content extraction.
```

Both `ohmd` and `ohhimark` are registered as entry points in `pyproject.toml`, both calling the same main function.

**Jina disclosure:** The `--help` epilog includes a note that the user-provided URL is sent to Jina's hosted API (`r.jina.ai`) for processing, per the requirements' transparency mandate. Example: `"Note: URLs are sent to Jina Reader (r.jina.ai) for content extraction."`

### URL validation

Before any network requests, the CLI validates the URL:

- Must have `http://` or `https://` scheme — reject everything else (exit code 1)
- Reject literal `localhost`, `127.0.0.1`, `::1` (exit code 1)
- Reject literal RFC 1918 private IPs: `10.*`, `172.16-31.*`, `192.168.*` (exit code 1)
- Reject literal link-local IPs: `169.254.*` (exit code 1)
- v1 does **not** resolve hostnames to detect private addresses

Implementation: `urllib.parse` to extract the host, `ipaddress` module to check whether a parsed IP is private. Hostname `localhost` is a simple string check.

### Exit code mapping

The CLI catches exceptions from the pipeline and maps them to exit codes:

| Exception | Exit code | Message |
|-----------|-----------|---------|
| URL validation failure | 1 | Describes what's wrong with the URL |
| `ProviderHTTPError` | 2 | "Jina returned HTTP {status}" |
| `ProviderRateLimitError` | 2 | "Rate limited. Setting JINA_API_KEY may help." |
| `ProviderEmptyContentError` | 2 | "Jina returned no usable content for this URL." |
| `ProviderUnreachableError` | 2 | "Could not reach Jina (r.jina.ai). Check your network connection." |
| `ProviderDecodeError` | 2 | "Jina response could not be decoded as text." |
| Filesystem conflict / write failure | 3 | Folder exists (suggests `--force`), or permissions/disk error |
| Any unhandled exception | 4 | "Unexpected error" with details |

All other modules raise exceptions or return values — the CLI is the sole boundary between the tool and the operating system.

---

## 8. Logging Module

Two outputs, one filter, and a timing consideration.

### Console output

Custom formatter using the spec's visual style:

| Symbol | Meaning |
|--------|---------|
| `✓` | Success (step completed, image downloaded) |
| `⚠` | Warning (image failed, resource threshold exceeded) |

**Cross-platform note:** Unicode symbols `✓` and `⚠` work on macOS, Linux, and modern Windows terminals. For older Windows terminals that don't support UTF-8, the module detects terminal encoding at startup and falls back to ASCII alternatives: `[OK]` and `[WARN]`.

No color output in v1 — deferred to v2 with `rich`.

### Log file

Written to `ohmd.log` inside the output folder. Full detail: HTTP status codes, response headers, response times, retry attempts with timestamps, file sizes, URL-to-filename mappings, stack traces on errors. Standard verbose formatter.

**Timing:** The file handler is attached as soon as the temp directory is created (pipeline step 6). It writes continuously throughout the run — no in-memory buffering needed. The handler is flushed and closed at pipeline step 10, before publish. The log file gets promoted along with everything else during the atomic rename.

### Redaction filter

A logging filter applied to both handlers that scrubs sensitive data before output:

- `Authorization` headers
- API keys / Bearer tokens
- Any other secrets

Prevents accidental exposure of credentials in `ohmd.log` or console output.

---

## 9. Pipeline Module

The orchestrator. A single `run()` function that calls modules in sequence and can short-circuit on failure.

### Sequence

```python
def run(url: str, output_dir: Path, force: bool) -> RunResult:
    # 1. Clean up stale temp directories (publisher)
    # 2. Check if final output path already exists (fail fast if not --force)
    # 3. Fetch markdown + metadata (provider)
    # 4. Generate slug from fetch result (writer)
    # 5. Extract image references (parser)
    # 6. Create temp directory, attach log file handler
    # 7. Download images (images module) — create images/ subfolder only if ≥1 image succeeds
    # 8. Rewrite markdown with local paths (parser)
    # 9. Assemble article.md in temp directory (writer)
    # 10. Flush and close log file handler
    # 11. Publish temp directory to final path (publisher)
    # 12. Return RunResult with outcome and stats
```

**Short-circuit behavior:** The existing-folder check (step 2) runs before any temp artifacts are created, so a conflict exits cleanly with no leftover files — per S-5 ("No files shall be modified"). If the provider raises an exception (step 3), we never reach step 5. If no images are found, steps 7 and 8 are skipped. Provider exceptions propagate to the CLI for exit code mapping — the pipeline does not catch them.

**`images/` subfolder creation (S-2):** The `images/` subfolder inside the temp directory is only created if at least one image download succeeds. If all images fail or there are no images, no `images/` folder exists in the output.

**Log file timing:** The log file handler is attached to the temp directory at step 6 and writes continuously from that point. Step 10 flushes and closes the handler — it does not "write" the log as a discrete step.

### Return type

```python
@dataclass
class RunResult:
    outcome: str           # "Success" or "Partial success"
    images_found: int
    images_downloaded: int
    images_failed: int
    output_path: Path
```

Carries enough information for the CLI to print the final summary line.

---

## 10. Config and Constants

All magic numbers and settings centralized in one module. No config file in v1.

### Timeouts

| Parameter | Value |
|-----------|-------|
| Jina connection timeout | 10 seconds |
| Jina read timeout | 60 seconds |
| Image connection timeout | 10 seconds |
| Image read timeout | 30 seconds |

### Retry

| Parameter | Value |
|-----------|-------|
| Max retries (images) | 3 (4 total attempts) |
| Backoff delays | 1s, 2s, 4s |
| Max redirect hops | 5 |

### Resource warning thresholds

| Parameter | Value |
|-----------|-------|
| Single image size warning | 10 MB |
| Total download size warning | 50 MB |
| Image count warning | 50 images |

### Other

| Parameter | Value |
|-----------|-------|
| Slug max length | 80 characters |
| Stale temp age threshold | 10 minutes |
| `JINA_API_KEY` env var name | `JINA_API_KEY` |
| Version string | `0.1.0` |
| Content-Type to extension map | See section 4 |

---

## 11. Error Propagation and Exit Codes

### Design principle

Exceptions flow up — the CLI catches them at the top. No module catches exceptions from another module except the CLI, which maps them to exit codes. This keeps error handling centralized and predictable.

### Exception hierarchy

```python
# Provider errors (exit code 2)
class ProviderError(Exception): ...
class ProviderHTTPError(ProviderError): ...         # 4xx/5xx (not 429), carries status_code
class ProviderRateLimitError(ProviderError): ...    # 429, suggests JINA_API_KEY
class ProviderEmptyContentError(ProviderError): ... # HTTP 200, empty/whitespace content
class ProviderUnreachableError(ProviderError): ...  # DNS failure, connection refused, network timeout
class ProviderDecodeError(ProviderError): ...       # Response cannot be decoded as text

# Filesystem errors (exit code 3)
class FilesystemError(Exception): ...              # Folder exists, permissions, disk full, rename failure
```

### Exit code mapping

| Source | Exception | Exit code | User-facing message |
|--------|-----------|-----------|---------------------|
| CLI | URL validation failure | 1 | Describes what's wrong with the URL |
| Jina provider | `ProviderHTTPError` | 2 | "Jina returned HTTP {status}: {message}" |
| Jina provider | `ProviderRateLimitError` | 2 | "Rate limited. Setting a JINA_API_KEY environment variable may help." |
| Jina provider | `ProviderEmptyContentError` | 2 | "Jina returned no usable content for this URL." |
| Jina provider | `ProviderUnreachableError` | 2 | "Could not reach Jina (r.jina.ai). Check your network connection." |
| Jina provider | `ProviderDecodeError` | 2 | "Jina response could not be decoded as text." |
| Publisher | `FilesystemError` (folder exists) | 3 | "Output folder already exists. Use --force to overwrite." |
| Publisher | `FilesystemError` (write/rename failure) | 3 | Descriptive error with path and OS error |
| Publisher | `FilesystemError` (`--force` rollback) | 3 | "Replacement failed. Original folder preserved." |
| Anywhere | Unhandled exception | 4 | "Unexpected error" with details |

### Flow

1. URL validation happens in the CLI *before* calling `pipeline.run()`. Failure exits immediately with code 1.
2. Provider exceptions propagate from the Jina module through the pipeline to the CLI.
3. Filesystem exceptions are raised by the publisher and propagate to the CLI.
4. The CLI wraps `pipeline.run()` in a try/except chain that catches each exception type in order, prints the appropriate message, and calls `sys.exit()` with the correct code.
5. A final catch-all `except Exception` handles anything unexpected with exit code 4.

---

## 12. Platform Assumptions and Known Limitations

### Atomic rename

The temp-to-final directory rename is atomic on macOS and Linux when source and destination are on the same filesystem. Our design guarantees this — the temp directory (`.ohmd-tmp-{uuid}`) is always created inside the same parent directory as the final output path.

### Supported platforms

| Platform | Status |
|----------|--------|
| macOS | Fully supported. Primary development platform. |
| Linux | Fully supported. Ubuntu 22.04+, common CI environments. |
| Windows | Best-effort. Atomic rename not guaranteed. Unicode console symbols may not render on older terminals. Not release-gated. |

### Python version

Python 3.10+ required. The codebase uses `str | None` union type syntax (PEP 604) which requires 3.10. CI matrix tests on 3.10, 3.11, and 3.12 across macOS and Linux.

### No concurrency

All operations are sequential — no threads, no async. This simplifies error handling, filesystem operations, and retry logic. See ADR-04.

### Network dependency

The tool requires internet access. Jina's hosted API (`r.jina.ai`) must be reachable for article fetching. Image URLs must be accessible from the user's network. No offline mode in v1.

### Known parser limitation

The regex parser does not handle parentheses in image URLs (T-22, best-effort). Such references are left unmodified in the output. See ADR-01.

---

## 13. Key Implementation Choices

| Decision | Choice | Rationale | Revisit trigger |
|----------|--------|-----------|-----------------|
| CLI framework | `argparse` | Stdlib, no dependency, sufficient for v1's simple interface | v2 adds subcommands or complex flag interactions → consider `click` |
| HTTP client | `requests` | Stable, ubiquitous, sync-only is fine with no concurrency | v2 adds concurrent downloads → consider `httpx` (supports async) |
| Markdown parsing | Regex | Sufficient for Jina's narrow output contract | Frequent parse failures or second provider → upgrade to AST parser |
| YAML serialization | Manual string building | Deterministic output matching spec exactly | 15+ configurable fields → switch to `pyyaml` |
| Date parsing | `python-dateutil` | Handles dozens of date formats without custom code | Unlikely to change |
| Logging | Stdlib `logging` | No dependency, dual-handler setup is straightforward | v2 rich console output → add `rich` as a handler |
| Concurrency | None (sequential) | Simplifies error handling, filesystem ops, and retry logic | Performance complaints on image-heavy articles |

### Dependencies summary

| Package | Purpose | Required |
|---------|---------|----------|
| `requests` | HTTP client for Jina API and image downloads | Yes |
| `python-dateutil` | Date string parsing for front matter normalization | Yes |
| `pytest` | Test framework | Dev only |
| `responses` or `pytest-httpserver` | HTTP mocking for unit tests | Dev only |
| `ruff` | Linter and formatter | Dev only |

Note: `pyyaml` is listed in the spec as a recommendation but may not be needed in v1 given the manual serialization decision. If other functionality requires it, it can be added.

---

## 14. ADRs (Architecture Decision Records)

### ADR-01: Regex-based markdown parsing

**Decision:** Use regex (`r'!\[(.*?)\]\(([^)]+)\)'`) to extract image references from markdown.

**Context:** The v1 input contract is narrowed to Jina Reader's actual output, which consistently emits standard `![alt](url)` syntax. An AST-based parser (e.g., `mistune`, `markdown-it-py`) would handle more edge cases but adds a dependency and complexity.

**Consequences:** Parentheses in URLs are a known limitation (T-22, best-effort). If future providers emit different patterns, the parser can be upgraded to AST-based.

**Revisit trigger:** If real-world usage reveals frequent parse failures, or if a second provider emits non-standard image syntax.

### ADR-02: Manual YAML front matter serialization

**Decision:** Build front matter YAML strings manually rather than using `pyyaml`'s `dump()`.

**Context:** The spec requires deterministic field ordering, consistent quoting (all values as quoted strings), and omission of empty optional fields. `pyyaml` sorts keys alphabetically by default and makes its own quoting decisions that may not match the spec.

**Consequences:** A small escape function is needed for special characters in values (double quotes, backslashes). Adding new fields requires adding `if` branches rather than just adding a key to a dict. Manageable for the small number of fields in v1 and v2.

**Revisit trigger:** If the tool grows to support 15+ configurable front matter fields with complex values.

### ADR-03: `requests` as HTTP client

**Decision:** Use `requests` for all HTTP operations (Jina API calls and image downloads).

**Context:** v1 is fully synchronous with no concurrent operations. `requests` is the most widely understood Python HTTP library, with a simple API and no async machinery. `httpx` offers both sync and async support but adds complexity that v1 doesn't need.

**Consequences:** If v2 adds concurrent image downloads, a migration to `httpx` would be needed. The APIs are similar, so migration cost is low.

**Revisit trigger:** If v2 adds concurrent downloads, or if `httpx`-specific features (HTTP/2 support, async) become needed.

### ADR-04: No concurrency in v1

**Decision:** All operations are sequential — Jina fetch, then images downloaded one by one.

**Context:** Concurrent downloads would improve performance for image-heavy articles but introduce complexity: race conditions in filename assignment, concurrent writes to the temp directory, interleaved retry logic, and harder-to-debug failure modes. The spec's performance target (5-image article in under 30 seconds) is achievable sequentially.

**Consequences:** Image-heavy pages (50+ images) will be slow. This is an edge case with a resource warning, not a typical use case.

**Revisit trigger:** If performance is a consistent user complaint for image-heavy articles.

### ADR-05: Stdlib `logging`

**Decision:** Use Python's stdlib `logging` module for all log output.

**Context:** `loguru` offers a simpler API and built-in formatting. `rich` offers colored, styled console output. However, stdlib `logging` requires no added dependency, supports dual-handler setup (console + file) natively, and custom formatters for the `✓`/`⚠` console style are straightforward to implement.

**Consequences:** Console output is plain text with Unicode symbols — no colors, no progress bars in v1. The custom formatter is ~20 lines of code.

**Revisit trigger:** If v2 adds `--verbose`/`--quiet` flags or rich console UI, `rich` can be added as a logging handler without replacing the infrastructure.
