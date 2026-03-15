# Project Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the oh-hi-markdown package structure, CI, and 28 stubbed test cases so that `pip install -e .` works, both entry points run, CI is green, and the test dashboard shows all 28 stubs.

**Architecture:** `src/oh_hi_markdown/` layout with 9 module files matching DESIGN.md boundaries plus `config.py` and `exceptions.py` (from DESIGN.md sections 10-11). Tests in `tests/` grouped by module. GitHub Actions CI with 6-cell matrix (Python 3.10/3.11/3.12 x Ubuntu/macOS). `mypy` deferred — no type checking config in v1.

**Tech Stack:** Python 3.10+, requests, python-dateutil, pytest, responses, ruff

---

## File Map

### Package (`src/oh_hi_markdown/`)

| File | Responsibility |
|------|---------------|
| `__init__.py` | Package init, exports `__version__` |
| `cli.py` | Argparse, entry points, URL validation, exit code mapping |
| `pipeline.py` | Orchestrates fetch -> parse -> download -> rewrite -> write -> publish |
| `provider.py` | `ContentProvider` protocol and `FetchResult` dataclass |
| `jina.py` | Jina Reader API implementation of `ContentProvider` |
| `parser.py` | Regex-based image extraction and URL rewriting |
| `images.py` | Image download, dedup, retry, Content-Type validation, filename resolution |
| `writer.py` | Front matter generation, slug, `article.md` assembly |
| `publisher.py` | Temp dir lifecycle, atomic rename, `--force` rollback, stale cleanup |
| `log.py` | Dual-output logging setup, redaction filter |
| `config.py` | Constants: timeouts, retry params, thresholds, version string |
| `exceptions.py` | `ProviderError` hierarchy and `FilesystemError` |

### Tests (`tests/`)

| File | Tests |
|------|-------|
| `conftest.py` | Shared fixtures: `sample_fetch_result`, `jina_success_response`, `png_bytes`, `jpg_bytes`, `svg_bytes` |
| `test_pipeline.py` | T-01, T-02 |
| `test_cli.py` | T-10, T-24, T-28 |
| `test_provider.py` | T-11, T-12, T-27 |
| `test_writer.py` | T-13, T-14, T-25 |
| `test_parser.py` | T-16, T-17, T-22 |
| `test_images.py` | T-03, T-04, T-05, T-15, T-19, T-26 |
| `test_images_retry.py` | T-06, T-07, T-23 |
| `test_publisher.py` | T-08, T-09, T-18, T-20, T-21 |

### CI (`.github/workflows/`)

| File | Responsibility |
|------|---------------|
| `ci.yml` | Lint (ruff) + test matrix (3 Pythons x 2 OSes) |

---

## Chunk 1: Package and config

### Task 1: Create `pyproject.toml`

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0", "setuptools-scm"]
build-backend = "setuptools.build_meta"

[project]
name = "oh-hi-markdown"
version = "0.1.0"
description = "CLI tool that downloads web articles as clean, AI-friendly markdown with locally-stored images"
readme = "README.md"
license = {text = "MPL-2.0"}
requires-python = ">=3.10"
authors = [{name = "Benny Lewis"}]
dependencies = [
    "requests>=2.28",
    "python-dateutil>=2.8",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "responses>=0.23",
    "ruff>=0.4",
]

[project.scripts]
ohmd = "oh_hi_markdown.cli:main"
ohhimark = "oh_hi_markdown.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pyproject.toml with package metadata and entry points"
```

---

### Task 2: Create package structure with stub modules

**Files:**
- Create: `src/oh_hi_markdown/__init__.py`
- Create: `src/oh_hi_markdown/cli.py`
- Create: `src/oh_hi_markdown/pipeline.py`
- Create: `src/oh_hi_markdown/provider.py`
- Create: `src/oh_hi_markdown/jina.py`
- Create: `src/oh_hi_markdown/parser.py`
- Create: `src/oh_hi_markdown/images.py`
- Create: `src/oh_hi_markdown/writer.py`
- Create: `src/oh_hi_markdown/publisher.py`
- Create: `src/oh_hi_markdown/log.py`
- Create: `src/oh_hi_markdown/config.py`
- Create: `src/oh_hi_markdown/exceptions.py`

- [ ] **Step 1: Create `__init__.py`**

```python
"""oh-hi-markdown: CLI tool for downloading web articles as AI-friendly markdown."""

__version__ = "0.1.0"
```

- [ ] **Step 2: Create `config.py`**

```python
"""Constants and configuration for oh-hi-markdown."""

VERSION = "0.1.0"

# Timeouts (seconds)
JINA_CONNECT_TIMEOUT = 10
JINA_READ_TIMEOUT = 60
IMAGE_CONNECT_TIMEOUT = 10
IMAGE_READ_TIMEOUT = 30

# Retry
MAX_IMAGE_RETRIES = 3  # 4 total attempts
BACKOFF_DELAYS = (1, 2, 4)
MAX_REDIRECT_HOPS = 5

# Resource warning thresholds
SINGLE_IMAGE_SIZE_WARNING = 10 * 1024 * 1024  # 10 MB
TOTAL_DOWNLOAD_SIZE_WARNING = 50 * 1024 * 1024  # 50 MB
IMAGE_COUNT_WARNING = 50

# Other
SLUG_MAX_LENGTH = 80
STALE_TEMP_AGE_SECONDS = 600  # 10 minutes
JINA_API_KEY_ENV = "JINA_API_KEY"
```

- [ ] **Step 3: Create `exceptions.py`**

```python
"""Exception hierarchy for oh-hi-markdown."""


class ProviderError(Exception):
    """Base class for provider failures."""


class ProviderHTTPError(ProviderError):
    """Jina returned 4xx/5xx (not 429). Carries status_code."""

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(message or f"HTTP {status_code}")


class ProviderRateLimitError(ProviderError):
    """Jina returned 429. Message suggests setting JINA_API_KEY."""


class ProviderEmptyContentError(ProviderError):
    """Jina returned HTTP 200 but content is empty/whitespace."""


class ProviderUnreachableError(ProviderError):
    """Jina host is unreachable (DNS failure, connection refused, network timeout)."""


class ProviderDecodeError(ProviderError):
    """Jina returned a response that cannot be decoded as text."""


class FilesystemError(Exception):
    """Folder exists, permissions, disk full, rename failure."""
```

- [ ] **Step 4: Create `cli.py` with `--version` support**

```python
"""CLI entry point for oh-hi-markdown."""

import argparse
import sys

from oh_hi_markdown.config import VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ohmd",
        description="Download web articles as clean, AI-friendly markdown with local images.",
        epilog="Note: URLs are sent to Jina Reader (r.jina.ai) for content extraction.",
    )
    parser.add_argument("url", nargs="?", help="URL of the article to download")
    parser.add_argument(
        "-o", "--output", default=".", help="Output directory (default: current directory)"
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing output folder")
    parser.add_argument("--version", action="version", version=f"ohmd {VERSION}")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.url is None:
        parser.print_help()
        sys.exit(1)

    # TODO: implement pipeline call
    print(f"ohmd {VERSION} — not yet implemented")
    sys.exit(0)
```

- [ ] **Step 5: Create remaining stub modules**

Each gets a docstring and nothing else:

`src/oh_hi_markdown/provider.py`:
```python
"""Content provider protocol and FetchResult dataclass."""
```

`src/oh_hi_markdown/jina.py`:
```python
"""Jina Reader API implementation of ContentProvider."""
```

`src/oh_hi_markdown/pipeline.py`:
```python
"""Pipeline orchestrator — calls modules in sequence."""
```

`src/oh_hi_markdown/parser.py`:
```python
"""Markdown image reference extraction and URL rewriting."""
```

`src/oh_hi_markdown/images.py`:
```python
"""Image download, deduplication, retry, and filename resolution."""
```

`src/oh_hi_markdown/writer.py`:
```python
"""Front matter generation, slug creation, and article.md assembly."""
```

`src/oh_hi_markdown/publisher.py`:
```python
"""Temp directory lifecycle, atomic publish, --force rollback, stale cleanup."""
```

`src/oh_hi_markdown/log.py`:
```python
"""Dual-output logging setup and redaction filter."""
```

- [ ] **Step 6: Commit**

```bash
git add src/
git commit -m "feat: add package structure with stub modules matching DESIGN.md"
```

---

### Task 3: Verify existing repo files

**Files:** (none created — verification only)

- [ ] **Step 1: Verify LICENSE exists and is MPL-2.0**

```bash
head -1 LICENSE
```

Expected: `Mozilla Public License Version 2.0`

- [ ] **Step 2: Verify .gitignore exists and covers Python artifacts**

```bash
grep -c "__pycache__" .gitignore
```

Expected: `1` (at least one match)

- [ ] **Step 3: Verify REQUIREMENTS.md is tracked in git**

```bash
git ls-files REQUIREMENTS.md
```

Expected: `REQUIREMENTS.md`

---

### Task 4: Verify install and entry points

**Files:** (none created — verification only)

- [ ] **Step 1: Install in dev mode**

```bash
pip install -e ".[dev]"
```

Expected: installs successfully, no errors.

- [ ] **Step 2: Verify `ohmd --version`**

```bash
ohmd --version
```

Expected output: `ohmd 0.1.0`

- [ ] **Step 3: Verify `ohhimark --version`**

```bash
ohhimark --version
```

Expected output: `ohmd 0.1.0`

- [ ] **Step 4: Verify both print the same thing**

```bash
diff <(ohmd --version) <(ohhimark --version)
```

Expected: no output (identical).

---

## Chunk 2: Test stubs and shared fixtures

### Task 5: Create shared test fixtures

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create empty `tests/__init__.py`**

```python
```

- [ ] **Step 2: Create `conftest.py` with shared fixtures**

```python
"""Shared test fixtures for oh-hi-markdown."""

import pytest


@pytest.fixture
def sample_fetch_result():
    """FetchResult with title, author, date, description, and 3 image refs (PNG, JPG, SVG).

    Used by: T-01, T-02 (no-images variant), T-13, T-14 (overrides title to None), T-25.
    """
    # Will be populated when provider.FetchResult is implemented
    pytest.skip("FetchResult not yet implemented")


@pytest.fixture
def jina_success_response():
    """JSON dict matching Jina's Accept: application/json response format.

    Used by: provider and pipeline tests.
    """
    return {
        "code": 200,
        "status": 20000,
        "data": {
            "title": "Test Article Title",
            "description": "A test article description",
            "url": "https://example.com/test-article",
            "content": "# Test Article\n\nSome content.\n\n"
            "![Test image](https://example.com/image1.png)\n\n"
            "![Another image](https://example.com/image2.jpg)\n\n"
            "![Diagram](https://example.com/diagram.svg)\n",
            "publishedTime": "2026-01-15T10:00:00Z",
            "usage": {"tokens": 42},
        },
    }


@pytest.fixture
def png_bytes():
    """Minimal valid 1x1 PNG image."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
        b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def jpg_bytes():
    """Minimal valid JPEG image."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00"
        b"\x01\x00\x01\x00\x00\xff\xd9"
    )


@pytest.fixture
def svg_bytes():
    """Minimal valid SVG image."""
    return b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
```

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "test: add shared fixtures in conftest.py"
```

---

### Task 6: Stub pipeline tests (T-01, T-02)

**Files:**
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write test stubs**

```python
"""Pipeline end-to-end tests (mocked HTTP)."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 5")
def test_t01_standard_article_with_images():
    """T-01: Standard article with 3 images: all download successfully,
    all links rewritten to local paths, front matter complete with correct field order."""


@pytest.mark.skip(reason="Not yet implemented — slice 4")
def test_t02_article_with_no_images():
    """T-02: Article with no images: article.md created, no images/ folder,
    run reports 'Success.'"""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: stub T-01, T-02 pipeline tests"
```

---

### Task 7: Stub CLI tests (T-10, T-24, T-28)

**Files:**
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write test stubs**

```python
"""CLI entry point and URL validation tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 1")
def test_t10_invalid_url_no_scheme():
    """T-10: Invalid URL input (no scheme): exit code 1, no files created,
    no HTTP requests made."""


@pytest.mark.skip(reason="Not yet implemented — slice 1")
def test_t24_private_url_rejected():
    """T-24: Private/internal URL rejected: literal private IPs and localhost
    cause exit code 1, no requests made."""


@pytest.mark.skip(reason="Not yet implemented — slice 12")
def test_t28_command_alias_equivalence():
    """T-28: Command alias equivalence: both ohmd and ohhimark entry points
    are installed and produce identical behavior."""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: stub T-10, T-24, T-28 CLI tests"
```

---

### Task 8: Stub provider tests (T-11, T-12, T-27)

**Files:**
- Create: `tests/test_provider.py`

- [ ] **Step 1: Write test stubs**

```python
"""Provider / Jina API error handling tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 2")
def test_t11_jina_http_500():
    """T-11: Jina returns HTTP 500: exit code 2, descriptive error,
    no output folder created."""


@pytest.mark.skip(reason="Not yet implemented — slice 2")
def test_t12_jina_rate_limit_429():
    """T-12: Jina returns HTTP 429 (rate limit): exit code 2,
    message suggests setting JINA_API_KEY."""


@pytest.mark.skip(reason="Not yet implemented — slice 2")
def test_t27_jina_empty_content():
    """T-27: Jina returns HTTP 200 but with empty or whitespace-only markdown:
    exit code 2, descriptive error, no output folder created."""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_provider.py
git commit -m "test: stub T-11, T-12, T-27 provider tests"
```

---

### Task 9: Stub writer tests (T-13, T-14, T-25)

**Files:**
- Create: `tests/test_writer.py`

- [ ] **Step 1: Write test stubs**

```python
"""Writer module tests: slug generation, title fallback, front matter."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 3")
def test_t13_title_with_special_characters():
    """T-13: Article title with special characters: slug is properly sanitized,
    folder created with correct name."""


@pytest.mark.skip(reason="Not yet implemented — slice 3")
def test_t14_title_empty_or_missing():
    """T-14: Article title is empty or missing: fallback naming applied
    per metadata fallback rules."""


@pytest.mark.skip(reason="Not yet implemented — slice 3")
def test_t25_front_matter_field_order_and_omission():
    """T-25: Front matter field order and omission: optional fields missing
    from Jina response are omitted (not blank), required fields present,
    field order matches spec."""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_writer.py
git commit -m "test: stub T-13, T-14, T-25 writer tests"
```

---

### Task 10: Stub parser tests (T-16, T-17, T-22)

**Files:**
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write test stubs**

```python
"""Parser module tests: image extraction edge cases."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t16_data_uri_ignored():
    """T-16: Image with data: URI in markdown: left unmodified,
    not downloaded, not counted in summary."""


@pytest.mark.skip(reason="Not yet implemented — slice 5")
def test_t17_empty_alt_text():
    """T-17: Markdown with empty alt text ![](url): image downloaded,
    empty alt preserved in output."""


@pytest.mark.skip(reason="Not yet implemented — slice 13")
def test_t22_parentheses_in_url():
    """T-22: Image URL containing parentheses or syntax that challenges
    the regex parser. Either processed correctly or left completely unmodified."""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_parser.py
git commit -m "test: stub T-16, T-17, T-22 parser tests"
```

---

### Task 11: Stub image download tests (T-03, T-04, T-05, T-15, T-19, T-26)

**Files:**
- Create: `tests/test_images.py`

- [ ] **Step 1: Write test stubs**

```python
"""Image download, dedup, and Content-Type validation tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t03_duplicate_image_url():
    """T-03: Duplicate image URL used twice in markdown: downloaded once,
    both references point to same local file."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t04_no_file_extension():
    """T-04: Image URL with no file extension: extension derived from
    Content-Type header."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t05_query_parameters():
    """T-05: Image URL with query parameters: parameters stripped from
    filename, image downloaded correctly."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t15_filename_collision():
    """T-15: Two images resolve to the same sanitized filename:
    disambiguated with suffix (-a, -b)."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t19_non_image_content_type():
    """T-19: Non-image response masquerading as image: image URL returns
    text/html. No file written, markdown URL unchanged, counted as failed."""


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t26_missing_content_type():
    """T-26: Missing Content-Type header with known image extension in URL:
    image accepted and saved. Missing Content-Type with no recognizable
    extension: treated as failed."""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_images.py
git commit -m "test: stub T-03, T-04, T-05, T-15, T-19, T-26 image tests"
```

---

### Task 12: Stub retry/error tests (T-06, T-07, T-23)

**Files:**
- Create: `tests/test_images_retry.py`

- [ ] **Step 1: Write test stubs**

```python
"""Image retry, failure, and redirect limit tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 7")
def test_t06_image_http_404_with_retry():
    """T-06: Image that returns HTTP 404: retried 3 times, skipped,
    original URL preserved in markdown, run reports 'Partial success' (exit 0).
    The failed image's number slot is consumed."""


@pytest.mark.skip(reason="Not yet implemented — slice 7")
def test_t07_all_images_fail():
    """T-07: All images fail: article.md still created with original URLs,
    images/ folder not created, run reports 'Partial success' (exit 0)."""


@pytest.mark.skip(reason="Not yet implemented — slice 7")
def test_t23_redirect_hop_limit():
    """T-23: Image request exceeds redirect-hop limit (5 hops). Treated as
    failed, original URL preserved, logged correctly."""
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_images_retry.py
git commit -m "test: stub T-06, T-07, T-23 retry/error tests"
```

---

### Task 13: Stub publisher tests (T-08, T-09, T-18, T-20, T-21)

**Files:**
- Create: `tests/test_publisher.py`

- [ ] **Step 1: Write test stubs**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_publisher.py
git commit -m "test: stub T-08, T-09, T-18, T-20, T-21 publisher tests"
```

---

## Chunk 3: CI, linting, and verification

### Task 14: Create GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/
git commit -m "ci: add lint + test matrix (3 Pythons x 2 OSes)"
```

---

### Task 15: Update README stub

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README with install instructions**

```markdown
# oh-hi-markdown

> CLI tool that downloads web articles as clean, AI-friendly markdown with locally-stored images.

**Status:** Work in progress

## Install

```bash
pip install git+https://github.com/Benny-Lewis/oh-hi-markdown
```

For development:

```bash
git clone https://github.com/Benny-Lewis/oh-hi-markdown
cd oh-hi-markdown
pip install -e ".[dev]"
```

## Usage

```bash
ohmd https://example.com/article
# or equivalently:
ohhimark https://example.com/article
```

Note: URLs are sent to Jina Reader (r.jina.ai) for content extraction.

## License

MPL-2.0
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with install and usage instructions"
```

---

### Task 16: Run linter and fix any issues

**Files:** (potential modifications to any `.py` file)

- [ ] **Step 1: Run ruff check**

```bash
ruff check src/ tests/
```

Expected: no errors. If there are errors, fix them.

- [ ] **Step 2: Run ruff format check**

```bash
ruff format --check src/ tests/
```

Expected: no formatting issues. If there are issues, run `ruff format src/ tests/` and commit.

- [ ] **Step 3: Commit if any fixes were needed**

```bash
git add -u
git commit -m "style: fix linting/formatting issues"
```

---

### Task 17: Run pytest and verify all 28 stubs are visible

**Files:** (none — verification only)

- [ ] **Step 1: Run pytest with verbose output**

```bash
pytest -v
```

Expected: 28 tests collected, all 28 skipped. Output should show each test name with `SKIPPED`.

- [ ] **Step 2: Verify test count**

```bash
pytest --co -q | tail -1
```

Expected: `28 tests collected`

---

### Task 18: Final verification

**Files:** (none — verification only)

- [ ] **Step 1: Verify `ohmd --version`**

```bash
ohmd --version
```

Expected: `ohmd 0.1.0`

- [ ] **Step 2: Verify `ohhimark --version`**

```bash
ohhimark --version
```

Expected: `ohmd 0.1.0`

- [ ] **Step 3: Run full test suite one more time**

```bash
pytest -v --tb=short
```

Expected: 28 skipped, 0 failed, 0 errors.

- [ ] **Step 4: Check git status is clean**

```bash
git status
```

Expected: nothing to commit, working tree clean.
