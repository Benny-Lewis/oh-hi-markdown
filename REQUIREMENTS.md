# Project Requirements: oh-hi-markdown

> A CLI tool that downloads web articles as clean, AI-friendly markdown with locally-stored images.

**Project name:** oh-hi-markdown
**CLI commands:** `ohmd` and `ohhimark` (identical, both installed)
**Package name:** `oh-hi-markdown` (import as `oh_hi_markdown`)
**Repository:** `github.com/Benny-Lewis/oh-hi-markdown`

**Version:** v1 (MVP)
**Last updated:** 2026-03-17
**Status:** ✅ Locked — v1 implementation baseline

> This document is the implementation contract for oh-hi-markdown v1. Changes from this point require a noted reason, updated date, and review before merging.

---

## Problem Statement

When preparing web articles for use in AI sessions (e.g., uploading to Claude, feeding into agents, building context windows), there is no single CLI tool that:

1. Extracts clean article content from a URL (stripping nav, ads, boilerplate)
2. Converts it to markdown (the most token-efficient format for LLMs)
3. Downloads images as separate local files
4. Rewrites image references in the markdown to use relative local paths
5. Includes AI-generated descriptions/captions for images

Existing tools solve pieces of this but not the full pipeline. Jina Reader produces excellent AI-optimized markdown but doesn't download images. Image-downloading tools like `markdown-image-downloader` handle localization but don't do content extraction. This tool bridges that gap.

---

## v1 Scope

### What it does

- Accepts a single URL as input
- Fetches clean, content-extracted markdown via Jina Reader API (using `X-With-Generated-Alt: true` for AI image captions when API key is set)
- Parses the markdown for image references
- Downloads each image to a local `images/` subfolder
- Rewrites image URLs in the markdown to relative local paths
- Preserves Jina's AI-generated alt text / captions
- Includes full article metadata as YAML front matter
- Outputs a self-contained folder: `article.md` + `images/`

### What it does NOT do (v1)

- Batch processing of multiple URLs (use a shell loop for now)
- Paywall or authentication handling
- Custom image filtering (decorative vs. content images)
- Custom vision model integration for image descriptions
- Alt text quality assessment or enhancement
- Configurable metadata fields (all fields included in v1)
- MCP server or Claude Code skill integration

### Not in scope, even if users ask

These are explicit exclusions that protect engineering from adjacent complexity during implementation:

- **No browser automation.** The tool does not launch, control, or depend on a browser. All browser-side rendering is delegated to Jina's hosted service.
- **No authenticated sessions.** No login, cookies, or session management. Paywalled or login-gated content is unsupported.
- **No JavaScript execution.** The tool does not run JS locally. Any JS rendering is handled server-side by Jina.
- **No OCR.** Images are saved as files, not analyzed for embedded text.
- **No image optimization or compression.** Images are saved as received. No resizing, recompression, or format conversion.
- **No preservation of original page layout.** The tool produces markdown, not a visual replica.
- **No embedded video or media download.** Only static images referenced in markdown image syntax are downloaded.
- **No resume or retry across separate runs.** Each invocation is a standalone, self-contained operation. There is no state persisted between runs.

### Supported content types

#### Supported

- Blog posts and engineering/tech articles
- News articles
- Essay-style and longform pages
- Article-like documentation pages with a clear primary content body
- Scientific paper landing pages (not raw PDFs)

#### Unsupported (may produce poor results or fail)

- Homepages and landing pages without a primary article body
- Search results pages
- RSS/Atom feeds
- Web applications, dashboards, and heavily interactive pages
- Authenticated or internal pages
- Raw PDF URLs (Jina may support these, but this tool does not target them)
- Pages with content primarily in video, audio, or interactive media

The tool does not validate content type before processing. Unsupported content types may produce unexpected output. This is documented, not prevented.

---

## User Workflow

### Basic usage

```bash
# Simplest invocation
ohmd https://example.com/some-article

# Specify output directory
ohmd https://example.com/some-article -o ~/articles

# Force overwrite if output folder already exists
ohmd https://example.com/some-article --force

# With Jina API key (higher rate limit)
export JINA_API_KEY=jina_your_key_here
ohmd https://example.com/some-article

# Both commands are identical
ohhimark https://example.com/some-article
```

### Expected output

```
./how-nuclear-batteries-work-a-deep-dive/
├── article.md
├── images/
│   ├── 001-reactor-diagram.png
│   ├── 002-power-output-chart.jpg
│   └── 003-comparison-table.png
└── ohmd.log
```

### Example markdown output

```markdown
---
title: "How Nuclear Batteries Work: A Deep Dive"
author: "Jane Smith"
date: "2026-03-10"
source_url: "https://example.com/how-nuclear-batteries-work-a-deep-dive"
description: "An exploration of radioisotope thermoelectric generators and their applications."
downloaded: "2026-03-13T14:30:00Z"
tool: "ohmd v0.1.0"
---

# How Nuclear Batteries Work: A Deep Dive

Nuclear batteries, also known as radioisotope thermoelectric generators (RTGs),
have powered spacecraft for decades...

![A cutaway diagram showing the internal structure of an RTG with labeled
components including the plutonium-238 fuel capsule, thermoelectric couples,
and heat dissipation fins](./images/001-reactor-diagram.png)

The power output varies significantly depending on the isotope used...
```

### Run outcome language

Every run is classified into one of three outcomes, reported in the console summary:

| Outcome | Meaning | Exit code |
|---|---|---|
| **Success** | Article saved and all images localized. | `0` |
| **Partial success** | Article saved, but one or more images failed to download. | `0` |
| **Failed** | Article extraction failed or required output could not be written. | Non-zero |

The console summary shall use the exact terms "Success," "Partial success," or "Failed" so users and scripts can parse the outcome.

---

## CLI Interface

```
usage: ohmd [-h] [-o OUTPUT] [--force] [--version] url
       ohhimark [-h] [-o OUTPUT] [--force] [--version] url

Download web articles as AI-friendly markdown with local images.

positional arguments:
  url                   URL of the article to download

optional arguments:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   output directory (default: current working directory)
  --force               overwrite output folder if it already exists
  --version             show version and exit
```

**Note:** `-v`/`--verbose` is deferred to post-v1. The v1 console output is fixed at medium detail (see Logging section). Adding `--verbose` and `--quiet` flags requires defining exactly what changes at each level, which is unnecessary scope for MVP.

---

## Internal Architecture Constraint: Pluggable Fetch Provider

Even though v1 ships with only one content provider (Jina Reader), the content-fetching layer shall be implemented behind an internal provider interface.

### Requirement

The module responsible for "given a URL, return markdown text and metadata" shall be a separate, self-contained component with a defined input/output contract. The image downloading, link rewriting, and file output logic shall not contain any Jina-specific code.

### Interface contract (internal, not user-facing in v1)

```python
class FetchResult:
    markdown: str           # The article content as markdown
    title: str | None       # Article title
    author: str | None      # Article author
    date: str | None        # Article publication date
    description: str | None # Article description / summary
    source_url: str         # The original URL

class ContentProvider(Protocol):
    def fetch(self, url: str) -> FetchResult: ...
```

### Rationale

The Jina dependency has known risk (hosted service, potential pricing changes). The tool architecture must allow swapping in `percollate`, self-hosted Jina, or `readability-cli` + `pandoc` without rewriting the image pipeline. This interface boundary makes that a localized change rather than a rewrite.

---

## Dependencies & External Services

### Runtime dependencies

| Dependency | Purpose | Risk |
|---|---|---|
| Jina Reader API (`r.jina.ai`) | Content extraction + markdown conversion + AI image captions | Medium — hosted service, but core is open source (Apache-2.0) and self-hostable. Underlying libraries (Readability.js, Turndown, Puppeteer) are independently maintained. |
| `requests` (Python) | HTTP client for image downloads | None — stable, ubiquitous |
| `pyyaml` (Python) | YAML front matter generation | None — stable, ubiquitous |

### Jina API key

- **Optional.** The tool checks for a `JINA_API_KEY` environment variable.
- Without a key: Jina imposes a lower rate limit (see Jina's current documentation for specifics).
- With a free key: higher rate limits. Key obtained at https://jina.ai (no credit card required as of this writing).
- The tool shall detect HTTP 429 responses and inform the user that an API key may help. The tool shall not hardcode specific rate-limit numbers in user-facing messages, since Jina may change these independently.

### Fallback strategy (post-v1)

If Jina's hosted API becomes unavailable or changes terms:

- The core content extraction can be replaced with `percollate`, self-hosted Jina, or `readability-cli` + `pandoc` by implementing a new `ContentProvider`.
- The image downloading and link rewriting logic (this tool's primary contribution) is entirely local and has no external dependencies.
- The AI image captioning (currently via Jina's `X-With-Generated-Alt`) can be replaced with Claude API or another vision model.

---

## Output Specification

### Folder structure

```
<output-dir>/<slugified-article-title>/
├── article.md          # The article content with local image references
├── images/             # Downloaded image files (only if ≥1 image succeeded)
│   ├── 001-name.ext
│   ├── 002-name.ext
│   └── ...
└── ohmd.log            # Detailed log of the download operation
```

### Folder naming

- Derived from the article title returned by Jina.
- Slugified: lowercase, hyphens for spaces, strip characters not in `[a-z0-9-]`.
- Maximum slug length: 80 characters (truncated at a word boundary).
- See "Metadata Fallback Rules" for behavior when title is missing or slug is empty.

### Image file naming

- Format: `{NNN}-{sanitized-original-filename}.{ext}`
- Sequential prefix `NNN` is zero-padded to 3 digits (001, 002, ...).
- Original filename extracted from the URL path, sanitized: strip query parameters, replace characters not in `[a-zA-Z0-9._-]` with `-`, collapse consecutive hyphens.
- If the URL has no meaningful filename (e.g., path is `/` or a bare hash), use `image` as the base name (e.g., `003-image.png`).
- Extension is determined by: (1) the `Content-Type` response header mapping, falling back to (2) the file extension in the URL. `.bin` is used only when `Content-Type` is a confirmed `image/*` subtype with no known extension mapping. If neither source identifies the content as an image, the download is treated as failed and no file is written (see Image Handling Rules).
- If two images would produce the same filename after sanitization, append `-a`, `-b`, etc. before the extension (e.g., `003-diagram.png`, `003-diagram-a.png`).

### Front matter

YAML front matter included at the top of every markdown file. v1 fields:

| Field | Source | Required | Example |
|---|---|---|---|
| `title` | Jina response / page title | Yes (see fallback rules) | `"How Nuclear Batteries Work"` |
| `author` | Jina response / page metadata | No | `"Jane Smith"` |
| `date` | Jina response / page metadata | No | `"2026-03-10"` |
| `source_url` | The input URL | Yes (always available) | `"https://example.com/..."` |
| `description` | Jina response / meta description | No | `"An exploration of..."` |
| `downloaded` | Timestamp of download | Yes (always available) | `"2026-03-13T14:30:00Z"` |
| `tool` | Tool name and version | Yes (always available) | `"ohmd v0.1.0"` |

See "Metadata Fallback Rules" and "Front Matter Serialization Rules" for detailed behavior.

---

## Acceptance Criteria

### Fetch

| ID | Criterion |
|---|---|
| F-1 | Given a valid, publicly accessible article URL, the tool shall retrieve markdown content from Jina Reader and proceed to the image processing step. |
| F-2 | When `JINA_API_KEY` is set, the Jina request shall include the `X-With-Generated-Alt: true` header. When no API key is configured, the header shall be omitted (Jina requires authentication for this feature). |
| F-3 | If a `JINA_API_KEY` environment variable is set, the tool shall include it as a Bearer token in the request. |
| F-4 | If Jina returns an HTTP error (4xx, 5xx) or is unreachable, the tool shall exit with exit code 2 and a descriptive error message. No output folder shall be created. |
| F-5 | If Jina returns a rate-limit response (429), the tool shall exit with exit code 2 and suggest that setting a `JINA_API_KEY` environment variable may resolve the issue. |
| F-6 | The fetch result shall be treated as failed (exit code 2) if any of the following are true: (a) the returned markdown is empty or whitespace-only, (b) the provider raises an exception, or (c) the response cannot be decoded as text. The error message shall indicate which condition was met. |

### Parse

| ID | Criterion |
|---|---|
| P-1 | The tool shall extract all inline markdown image references matching the subset of `![alt](url)` syntax emitted by Jina Reader in practice (see Supported Input Contract). |
| P-2 | HTML `<img>` tags in the markdown are best-effort only in v1 and are not guaranteed to be processed. If an `<img>` tag is encountered and not processed, it shall be left unmodified in the output. |
| P-3 | Images inside markdown link constructs (`[![alt](img-url)](link-url)`) are best-effort only in v1. If encountered and not processed, they shall be left unmodified. |
| P-4 | Data URIs (`data:image/...`) shall be ignored and left unmodified in the output. |

### Download

| ID | Criterion |
|---|---|
| D-1 | Each image URL extracted in the parse step shall be attempted via HTTP GET. Successful downloads shall be written to the `images/` subfolder. |
| D-2 | If the same URL appears multiple times in the markdown, it shall be downloaded once. All references to that URL shall point to the same local file. |
| D-3 | If two different URLs resolve to the same filename after sanitization, the filenames shall be disambiguated (see Image file naming). |
| D-4 | Images shall be downloaded sequentially, not concurrently. |
| D-5 | Each image download shall have a timeout of 30 seconds. |
| D-6 | If an image download fails, it shall be retried up to 3 times after the initial attempt (4 total attempts) with exponential backoff (1s, 2s, 4s delays before each retry). |
| D-7 | If all retries fail for an image, the tool shall skip that image, log a warning, print a console warning, and leave the original remote URL in the markdown. |
| D-8 | HTTP redirects (301, 302, 307, 308) shall be followed up to 5 hops. If the redirect limit is exceeded, the download shall be treated as failed. |
| D-9 | The `Referer` header shall be set to the original article URL on all image requests, to handle hotlink-protected images. |
| D-10 | There is no maximum image file size enforced in v1. However, a console warning shall be emitted for any single image exceeding 10 MB, and for total image download size exceeding 50 MB. |
| D-11 | There is no maximum image count enforced in v1. However, a console warning shall be emitted if more than 50 images are found. |
| D-12 | SVG images shall be saved as-is (`.svg` file). No rasterization. |
| D-13 | Duplicate image binaries at different URLs are not deduplicated in v1. Each unique URL produces a separate file. |
| D-14 | If the HTTP response `Content-Type` is not `image/*`, the download shall be treated as failed. No local file shall be written. The original remote URL shall remain in the markdown. This prevents saving HTML error pages, anti-hotlink pages, or CDN error responses as image files. |

### Rewrite

| ID | Criterion |
|---|---|
| R-1 | For each successfully downloaded image, the markdown image reference shall be rewritten from the remote URL to a relative local path: `./images/{filename}`. |
| R-2 | The alt text of each image reference shall be preserved exactly as received from Jina. |
| R-3 | For images that failed to download (including non-image responses), the original remote URL shall remain in the markdown, unmodified. |

### Save

| ID | Criterion |
|---|---|
| S-1 | Given successful article extraction, the tool shall always create the output folder, `article.md`, and `ohmd.log`, even if all image downloads fail. |
| S-2 | The `images/` subfolder shall only be created if at least one image was successfully downloaded. |
| S-3 | `article.md` shall contain the YAML front matter followed by the processed markdown content. |
| S-4 | All file writes shall target a temporary directory first. The temp directory shall be renamed to the final output path only after all required artifacts for that run (`article.md`, `ohmd.log`, and any successfully downloaded images) are fully written and closed. (See Atomic Write Behavior.) |
| S-5 | If the final output folder already exists and `--force` was not passed, the tool shall exit with exit code 3 and a message telling the user the folder exists and suggesting `--force`. No files shall be modified. |
| S-6 | If `--force` was passed and the folder exists, the new result shall be built completely in a temp directory first. Only after successful completion shall the old folder be replaced. (See Conflict / Overwrite Behavior.) |

### Log

| ID | Criterion |
|---|---|
| L-1 | Console output shall show: article fetch status, each image download result (success with filename and size, or failure with URL and reason), and a final summary line using "Success," "Partial success," or "Failed" language. |
| L-2 | `ohmd.log` shall contain: full HTTP status codes, response headers (Content-Type, Content-Length), response times, retry attempts with timestamps, file sizes, image URL-to-filename mappings, Jina response metadata, and any errors with stack traces. |
| L-3 | The log file shall be written inside the output folder. |
| L-4 | Resource warnings (image size > 10 MB, total size > 50 MB, image count > 50) shall appear in both console output and the log file. |

### Overall run

| ID | Criterion |
|---|---|
| O-1 | The run shall exit with code `0` if article extraction succeeds and `article.md` is written, even if some or all image downloads fail. |
| O-2 | A summary shall be printed at the end of every successful or partially successful run showing: outcome label ("Success" or "Partial success"), number of images found, number successfully downloaded, number failed. |
| O-3 | If the run fails (article extraction failed, filesystem error, etc.), the summary shall print "Failed" with the reason. |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success or partial success. Article saved. Some image download failures may have occurred (see summary output). |
| `1` | Invalid input. URL failed validation, required arguments missing, or URL targets a literal private/internal IP address or `localhost`. |
| `2` | Article extraction failed. Jina returned an error, was unreachable, rate-limited, or returned empty/unusable content (see F-4, F-5, F-6). |
| `3` | Filesystem conflict or write failure. Output folder already exists (without `--force`), or the tool could not write to the target directory (permissions, disk full, etc.). |
| `4` | Unexpected internal error. Unhandled exception. |

---

## Conflict / Overwrite Behavior

### v1 default: fail safely

If the target output folder already exists:

1. The tool shall **not** overwrite, modify, or delete the existing folder.
2. The tool shall exit with exit code 3.
3. The error message shall state that the folder exists and suggest using `--force` to overwrite.

### `--force` flag: safe replacement

When `--force` is passed and the folder exists:

1. The new result is built completely in a temp directory (per the normal atomic-write flow).
2. After the new result is fully complete (all required artifacts written and closed):
   a. The existing folder is renamed to a backup: `<folder>.ohmd-backup-{uuid}`.
   b. The temp directory is renamed to the final output folder name.
   c. If step 2b fails (e.g., permissions, filesystem error): the backup is restored to the original name, the temp directory is left in place, and the tool exits with code 3 and a descriptive error. The user's original output is preserved.
   d. If step 2b succeeds: the backup folder is deleted.
3. If the new run fails before step 2 (fetch error, write error, interrupt):
   a. The temp directory is cleaned up (or left for debugging per temp cleanup rules).
   b. The existing folder remains **completely intact and unmodified**.
4. A console message shall note that the existing folder was replaced.

### Rationale

This prevents the failure mode where `--force` deletes known-good output and then the new run fails, leaving the user with nothing.

### Future versions

- `--on-conflict {fail,overwrite,suffix}` flag to let users choose behavior.
- `suffix` mode creates a new folder with a timestamp appended (e.g., `article-title-20260313-143000/`).

---

## Metadata Fallback Rules

### Title

The title is used for both front matter and folder slug. The following fallback chain is evaluated in order; the first step that produces a non-empty slug wins:

| Priority | Source | Slug derivation | Front matter `title` value |
|---|---|---|---|
| 1 | Jina returns a title | Slugify the title (lowercase, hyphens, strip non-`[a-z0-9-]`). | The Jina title. |
| 2 | Priority 1 slug is empty, but title contains transliterable non-ASCII characters | Transliterate (e.g., `ü` → `u`, `é` → `e`), then slugify. | The original (non-transliterated) Jina title. |
| 3 | No usable title from Jina, but markdown contains an H1 heading | Slugify the H1 text (with transliteration if needed, as in priority 2). | The H1 text. |
| 4 | No title and no H1, but URL has a meaningful path (more than just `/`) | Slugify the URL path component (e.g., `/some-article` → `some-article`). | The URL domain + path (e.g., `"example.com/some-article"`). |
| 5 | All above produce an empty slug | Timestamp slug: `article-YYYYMMDD-HHMMSS`. | The full URL. |

### Other metadata fields

| Field | If missing or empty |
|---|---|
| `author` | Omit the field from front matter entirely. |
| `date` | Omit the field from front matter entirely. |
| `description` | Omit the field from front matter entirely. |
| `source_url` | Always present (it is the user's input). |
| `downloaded` | Always present (generated by the tool). |
| `tool` | Always present (hardcoded). |

### Date normalization

- If a date is present, normalize to ISO 8601 format: `YYYY-MM-DD`.
- If the date string cannot be parsed, include it as-is in a string field and log a warning.

### Title consistency

- The `title` field in front matter and the markdown H1 heading are allowed to differ. The front matter title comes from page metadata; the H1 comes from article content. Neither is modified to match the other.

---

## Front Matter Serialization Rules

To ensure deterministic field ordering, consistent serialization format, and reliable tests (note: the `downloaded` timestamp varies per run, so output is not byte-for-byte identical across runs):

### Field order (fixed)

Front matter fields shall always appear in this order:

1. `title`
2. `author` (if present)
3. `date` (if present)
4. `source_url`
5. `description` (if present)
6. `downloaded`
7. `tool`

### Omission rules

- Optional fields that are missing or empty are **omitted entirely** — not emitted as blank strings, `null`, or empty values.

### Serialization format

- All scalar values are serialized as YAML quoted strings.
- The `downloaded` timestamp uses ISO 8601 with timezone: `"YYYY-MM-DDTHH:MM:SSZ"`.
- The front matter block is delimited by `---` on its own line, both above and below.

---

## Image Handling Rules

This is the core value of the tool. These rules define exactly what is downloaded, how, and what happens in edge cases.

### What counts as an image to download

- Any standard markdown image reference: `![any alt text](url)` where the URL uses `http://` or `https://` scheme.
- `data:` URIs are not images to download. They are left unmodified.
- Bare URLs not in image syntax are not processed.
- HTML `<img>` tags are best-effort only (see P-2).

### Content-Type validation

- After a successful HTTP response, the `Content-Type` header shall be checked.
- If the `Content-Type` is not `image/*`, the response shall be discarded and the download treated as failed.
- If the `Content-Type` header is missing entirely, the URL file extension is checked. If the extension maps to a known image type (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.avif`, `.bmp`, `.tiff`), the download is accepted and the extension determines the file type. If the extension does not map to a known image type or is absent, the download is treated as failed.
- This prevents saving HTML error pages, anti-hotlink redirect pages, CDN error pages, or other non-image content as local files.

### Deduplication

- **URL-level deduplication:** If the same URL appears in multiple image references, the image is downloaded once. All references to that URL point to the same local file.
- **Content-level deduplication:** Not performed in v1. Two different URLs that happen to serve the same binary produce two separate files.

### Image numbering

Sequential numbers (`001`, `002`, ...) are assigned as follows:

- Numbers are assigned in **markdown parse order** — the order in which unique image URLs are first encountered when scanning the markdown from top to bottom.
- A duplicate URL that appears later in the markdown **does not** consume a new number. All references to that URL reuse the filename assigned at first encounter.
- Failed downloads **do** consume their assigned number slot. If image `002` fails, the next image is `003`, not `002`. This keeps the numbering stable across re-runs regardless of transient network conditions, and ensures that the number-to-URL mapping logged in `ohmd.log` is consistent.

### Download behavior

| Parameter | Value |
|---|---|
| Timeout per image | 30 seconds |
| Max retries | 3 retries after initial attempt (4 total attempts) |
| Retry backoff | Exponential: 1s, 2s, 4s delay before each retry |
| Redirect limit | 5 hops |
| Concurrent downloads | No. Sequential only. |
| Referer header | Set to the original article URL |
| User-Agent header | `ohmd/{version}` |
| Max file size | No hard limit. Warning emitted above 10 MB per image. |
| Max image count | No hard limit. Warning emitted above 50 images. |
| Max total download size | No hard limit. Warning emitted above 50 MB total. |

### Filename resolution

1. Extract the filename from the URL path component (after the last `/`, before any `?`).
2. URL-decode the filename.
3. Sanitize: replace characters not in `[a-zA-Z0-9._-]` with `-`. Collapse consecutive hyphens.
4. If the result is empty, use `image` as the base name.
5. Determine the extension: prefer `Content-Type` header mapping, fall back to URL extension. The `.bin` extension is used only when the `Content-Type` is a confirmed `image/*` subtype that does not map to a known extension. If neither `Content-Type` nor URL extension identifies the content as an image, the download is treated as failed (see Content-Type validation) and this step is not reached.
6. Prepend the sequential number: `{NNN}-{sanitized-name}.{ext}`.
7. If the resulting filename collides with an existing file in the same batch, append `-a`, `-b`, etc. before the extension.

### Content-Type to extension mapping

| Content-Type | Extension |
|---|---|
| `image/png` | `.png` |
| `image/jpeg` | `.jpg` |
| `image/gif` | `.gif` |
| `image/webp` | `.webp` |
| `image/svg+xml` | `.svg` |
| `image/avif` | `.avif` |
| `image/bmp` | `.bmp` |
| `image/tiff` | `.tiff` |
| Any other `image/*` | Use URL extension if available, else `.bin` |
| Non-`image/*` Content-Type | **Treated as failed download. No file written.** |
| Missing Content-Type header | Accept if URL extension maps to known image type; otherwise **treated as failed download.** |

### SVG handling

SVG files are saved as-is (text/XML content). No rasterization, no modification.

### Failed image behavior

When an image fails after all retries, or returns a non-image Content-Type:

1. The image is skipped (no file written to `images/`).
2. The markdown reference is left unmodified (original remote URL preserved).
3. A warning is logged to `ohmd.log` with the URL, HTTP status (if any), Content-Type (if relevant), and error details.
4. A console warning is printed.
5. The failed image is included in the end-of-run summary count.

---

## Atomic Write / Partial Failure Behavior

### Guarantee

The tool shall not leave a partially written folder at the **final output path**. Temporary work directories may remain after interruption or crash and may be cleaned up on a later run.

### Implementation

1. All output is written to a temporary directory inside the output parent directory, named `.ohmd-tmp-{uuid}`.
2. The temp directory contains a marker file `.ohmd-marker` written immediately on creation to identify it as a tool-created temp directory.
3. Images are downloaded into the temp directory's `images/` subfolder.
4. `article.md` is written to the temp directory.
5. `ohmd.log` is written to the temp directory.
6. Only after all required artifacts (`article.md`, `ohmd.log`, and any successfully downloaded images) are fully written and closed, the temp directory is renamed to the final output folder name. This rename is atomic on macOS and Linux when source and destination are on the same filesystem.
7. If the tool exits before step 6 (crash, interrupt, error), the temp directory remains on disk.

### Stale temp directory cleanup

On startup, the tool shall check for `.ohmd-tmp-*` directories in the output parent directory and clean them up subject to these safety rules:

1. **Only delete directories that contain a `.ohmd-marker` file.** This prevents accidentally deleting unrelated directories that happen to match the naming pattern.
2. **Only delete directories whose `.ohmd-marker` file was last modified more than 10 minutes ago.** This prevents one invocation from deleting another invocation's active temp directory.
3. **Log each cleanup action** to the console (stderr). If the run later produces an output folder successfully, the cleanup summary shall also be included in `ohmd.log`. Cleanup messages are not written to a log file at the time of cleanup, because the output folder does not yet exist.

### Platform note

Atomic rename behavior is guaranteed on macOS and Linux in the supported same-filesystem case. Windows support for atomic rename is best-effort in v1 and is not release-gated.

---

## Logging

### Console output (v1 — fixed detail level)

Progress indicators for each step, warnings, and a final summary:

```
Fetching article from https://example.com/article...
✓ Article retrieved: "How Nuclear Batteries Work: A Deep Dive"
Downloading images (3 found)...
  ✓ 001-reactor-diagram.png (145 KB)
  ✓ 002-power-output-chart.jpg (89 KB)
  ⚠ 003-broken-image.png — failed after 3 retries (HTTP 404), skipping
✓ Markdown saved to ./how-nuclear-batteries-work/article.md

Partial success: 2 of 3 images downloaded, 1 failed
Output: ./how-nuclear-batteries-work/
```

Resource warnings appear inline when triggered:

```
  ⚠ 004-hero-banner.png — warning: 12.3 MB (large file)
  ⚠ Warning: total image download size exceeds 50 MB (67.2 MB)
```

### Log file

- Written to `ohmd.log` inside the output folder.
- Contains full detail: HTTP status codes, response headers (Content-Type, Content-Length), response times, retry attempts with timestamps, file sizes, image URL-to-filename mappings, Jina response metadata, resource warnings, and any errors with stack traces.
- **Log redaction:** Authorization headers, API keys, Bearer tokens, and any other secrets shall never be written to the log file or console output.
- Overwrites on each run (not appended), since atomic writes mean the folder is recreated on each run anyway.
- **The log file only exists for runs that reach the output-creation stage.** Early failures (invalid URL, Jina fetch error, filesystem conflict) produce console/stderr output only. There is no persistent log artifact for runs that fail before an output folder is created.

### Future versions

- `--verbose` flag for detailed console output (all log-level detail printed to console).
- `--quiet` flag for minimal console output (errors and summary only).
- Improved CLI UI (progress bars, colors via `rich` or similar).

---

## Supported Input Contract (Markdown Parsing)

### v1 officially supports

v1 supports the subset of inline markdown image syntax emitted by Jina Reader in practice. Specifically:

- Standard markdown image syntax: `![alt text](url)`
- Images with empty alt text: `![](url)`
- Images with multi-line alt text (Jina sometimes emits these for long AI captions)
- Images where the URL contains query parameters or fragments

URLs or constructs outside Jina's emitted subset are unsupported unless explicitly covered by tests.

### Best-effort only (not guaranteed)

- HTML `<img>` tags present in the markdown output
- Images nested inside link constructs: `[![alt](img-url)](link-url)`
- Images using markdown reference-style syntax: `![alt][ref]` with `[ref]: url` elsewhere
- Image URLs containing literal parentheses

If a best-effort pattern is encountered and cannot be processed, it shall be left **completely unmodified** in the output. It shall not be corrupted, partially rewritten, or removed.

### Not supported

- Data URIs (`data:image/...`) — left unmodified
- CSS background images — not visible in markdown
- Images loaded via JavaScript — not visible in markdown

### Rationale

Jina Reader consistently emits standard `![alt](url)` syntax. By narrowing the v1 parse contract to Jina's actual output, regex is an acceptable implementation choice. If future providers emit different patterns, the parser can be upgraded to an AST-based approach at that time.

---

## Security & Privacy

### URL validation

- The tool shall reject URLs with schemes other than `http://` and `https://` (exit code 1).
- The tool shall reject URLs containing literal localhost IPs (`127.0.0.1`, `::1`), literal RFC 1918 private IPs (`10.*`, `172.16-31.*`, `192.168.*`), literal link-local IPs (`169.254.*`), and the hostname `localhost`. Exit code 1 with a descriptive message.
- v1 does **not** perform DNS resolution of hostnames to detect private addresses. Hostname-based private-address blocking is deferred to a future version.

### Third-party data submission

- The user-provided URL is sent to Jina's hosted API (`r.jina.ai`). Users should be aware that Jina processes the target URL on their infrastructure.
- The tool shall note this in `--help` output or README, not suppress it.

### Image download safety

- Images are fetched from arbitrary remote URLs found in the article. The tool does not validate that image URLs belong to the same domain as the article.
- The `Referer` header is intentionally set to the article URL on image requests to improve compatibility with hotlink-protected images. This behavior should be documented in the README.

---

## Error Handling

### Image download failures

1. Retry up to 3 times after the initial attempt (4 total attempts) with exponential backoff (1s, 2s, 4s).
2. If the response `Content-Type` is not `image/*`, treat as failed immediately (no retry).
3. If all retries fail: skip the image, log a warning, notify the user via console.
4. The markdown retains the original remote URL for failed images.
5. A summary of failed downloads is printed at the end of the run.

### Jina API failures

- If Jina returns an HTTP error (4xx, 5xx) or is unreachable, the tool exits with exit code 2 and a descriptive error message.
- If rate-limited (429), the tool exits with exit code 2 and suggests that setting a `JINA_API_KEY` environment variable may help.
- If Jina returns HTTP 200 but the markdown content is empty, whitespace-only, or cannot be decoded as text, the tool exits with exit code 2 and a descriptive error message.

### Invalid URLs

- URLs must have `http://` or `https://` scheme and a non-empty host.
- URLs targeting literal private/internal IP addresses or `localhost` are rejected (see Security & Privacy).
- Invalid URLs cause exit code 1 with a clear error message.
- No request is made for invalid URLs.

### Filesystem errors

- If the output directory is not writable, exit code 3.
- If the output folder already exists and `--force` was not given, exit code 3.
- If disk space is exhausted during writes, exit code 3. Temp directory cleanup is attempted.

---

## Non-Functional Requirements

### Supported platforms

- **macOS:** Supported. Primary development platform.
- **Linux:** Supported. Ubuntu 22.04+, common CI environments.
- **Windows:** Best-effort in v1. Not actively tested. Not release-gated. Atomic rename behavior is not guaranteed on Windows.

### Python version

- Minimum: Python 3.10
- Tested on: 3.10, 3.11, 3.12 (CI matrix on macOS and Linux)

### Network

| Parameter | Value |
|---|---|
| Connection timeout | 10 seconds |
| Read timeout (images) | 30 seconds |
| Read timeout (Jina fetch) | 60 seconds |
| User-configurable timeouts | No (v1) |

### Performance expectations

- A typical article with 5 images should complete in under 30 seconds on a reasonable connection.
- No concurrency in v1. All operations are sequential.
- Image-heavy pages (50+ images, large total size) may be slow. Resource warnings are emitted at the thresholds defined in Image Handling Rules.

### Unicode / path handling

- Article titles may contain any Unicode characters. Slugification attempts transliteration of common non-ASCII characters before stripping.
- Filenames are restricted to `[a-zA-Z0-9._-]` after sanitization.
- The tool shall not produce paths longer than 255 characters per component. Slugs and filenames are truncated if necessary.

---

## Testing Strategy

### Framework

- `pytest`
- Mocked HTTP responses for unit tests via `responses` or `pytest-httpserver` (no live API calls in CI)
- Optional integration test suite that hits real URLs (run manually, not in CI)

### Required unit tests

| ID | Scenario |
|---|---|
| T-01 | Standard article with 3 images: all download successfully, all links rewritten to local paths, front matter complete with correct field order. |
| T-02 | Article with no images: `article.md` created, no `images/` folder, run reports "Success." |
| T-03 | Duplicate image URL used twice in markdown: downloaded once, both references point to same local file. |
| T-04 | Image URL with no file extension: extension derived from Content-Type header. |
| T-05 | Image URL with query parameters: parameters stripped from filename, image downloaded correctly. |
| T-06 | Image that returns HTTP 404: retried 3 times, skipped, original URL preserved in markdown, run reports "Partial success" (exit 0). The failed image's number slot is consumed (e.g., if image `002` fails, next image is `003`). |
| T-07 | All images fail: `article.md` still created with original URLs, `images/` folder not created, run reports "Partial success" (exit 0). |
| T-08 | Output folder already exists, no `--force`: exit code 3, no files modified, existing folder untouched. |
| T-09 | Output folder already exists, `--force` passed: old folder replaced, new output created. |
| T-10 | Invalid URL input (no scheme): exit code 1, no files created, no HTTP requests made. |
| T-11 | Jina returns HTTP 500: exit code 2, descriptive error, no output folder created. |
| T-12 | Jina returns HTTP 429 (rate limit): exit code 2, message suggests setting `JINA_API_KEY`. |
| T-13 | Article title with special characters: slug is properly sanitized, folder created with correct name. |
| T-14 | Article title is empty or missing: fallback naming applied per metadata fallback rules. |
| T-15 | Two images resolve to the same sanitized filename: disambiguated with suffix (`-a`, `-b`). |
| T-16 | Image with `data:` URI in markdown: left unmodified, not downloaded, not counted in summary. |
| T-17 | Markdown with empty alt text `![](url)`: image downloaded, empty alt preserved in output. |
| T-18 | Atomic write: if write fails after images are downloaded, no final output folder exists at the target path. |
| T-19 | Non-image response masquerading as image: image URL returns `text/html`. No file written, markdown URL unchanged, counted as failed in summary. |
| T-20 | `--force` replacement safety: valid output folder exists, `--force` used, new run fails during fetch. Old folder remains intact and unmodified. |
| T-21 | Temp cleanup safety: a recently-modified temp directory exists (< 10 minutes old). Cleanup does not delete it. |
| T-22 | Image URL containing parentheses or syntax that challenges the regex parser. Either processed correctly or left completely unmodified. |
| T-23 | Image request exceeds redirect-hop limit (5 hops). Treated as failed, original URL preserved, logged correctly. |
| T-24 | Private/internal URL rejected: literal private IPs (e.g., `http://192.168.1.1/article`) and `localhost` cause exit code 1, no requests made. Non-literal hostnames that happen to resolve to private IPs are not blocked in v1. |
| T-25 | Front matter field order and omission: optional fields missing from Jina response are omitted (not blank), required fields present, field order matches spec. |
| T-26 | Missing Content-Type header with known image extension in URL: image accepted and saved. Missing Content-Type with no recognizable extension: treated as failed. |
| T-27 | Jina returns HTTP 200 but with empty or whitespace-only markdown: exit code 2, descriptive error, no output folder created. |
| T-28 | Command alias equivalence: both `ohmd` and `ohhimark` entry points are installed and produce identical behavior and output for the same input URL. |

### Required integration tests (run manually)

| ID | Scenario |
|---|---|
| I-01 | Real tech blog post with mixed image types (PNG, JPG, SVG). |
| I-02 | Real news article with hero image and inline photos. |
| I-03 | Real documentation page with diagrams and code screenshots. |
| I-04 | Article with many images (10+). |
| I-05 | Article where some images are hotlink-protected. |

Specific URLs for integration tests shall be selected during development based on real-world testing. They shall be documented in the test suite with notes on what each exercises.

### Release gate

All required unit tests (T-01 through T-28) must pass on a clean environment (macOS and Linux) before v1 is tagged.

---

## Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.10+ | Wide compatibility for public open source tool |
| Package format | pip-installable (`pip install git+...`, eventually PyPI) | Standard distribution, easy for users |
| License | MPL-2.0 | File-level copyleft, doesn't infect larger works |
| Content extraction | Jina Reader API | Best AI-optimized markdown output, zero local dependencies for v1 |
| Image captions | Jina `X-With-Generated-Alt` (v1), own vision model (v2+) | Leverages existing free service for MVP, replaceable later |
| Architecture | Pluggable content provider interface | Isolates Jina dependency; reduces future rewrite cost |
| Markdown parsing | Regex for Jina-emitted `![alt](url)` | Sufficient for narrowed v1 input contract; upgradeable to AST parser if needed |

*Note: Specific library choices (e.g., `requests`, `pyyaml`, `pytest`) are recommendations, not requirements. Engineering may substitute equivalent libraries if justified.*

---

## Future Roadmap & Backlog

See [BACKLOG.md](BACKLOG.md) for v2+ feature ideas, deferred code quality items, and open questions.
