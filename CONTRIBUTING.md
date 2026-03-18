# Contributing to oh-hi-markdown

## Setup

```bash
git clone https://github.com/Benny-Lewis/oh-hi-markdown.git
cd oh-hi-markdown
pip install -e ".[dev]"
```

## Running tests

```bash
# Unit tests (all HTTP is mocked, no network required)
python -m pytest --tb=short -q

# Lint
ruff check && ruff format --check
```

## Code style

- Formatted and linted with [Ruff](https://docs.astral.sh/ruff/)
- Line length: 100 characters
- Target: Python 3.10+

## Project structure

```
src/oh_hi_markdown/
├── cli.py          # Argument parsing, URL validation, entry point
├── jina.py         # Jina Reader API client (ContentProvider implementation)
├── parser.py       # Markdown image reference extraction
├── images.py       # Image downloading, retry, filename resolution
├── writer.py       # Front matter generation and article.md assembly
├── publisher.py    # Atomic publish (temp dir → final output)
├── pipeline.py     # Orchestrates the full fetch → publish flow
├── log.py          # Logging setup, redaction, console output
├── config.py       # Constants and version
└── exceptions.py   # Custom exception types
```

## Architecture

The tool uses a pluggable content provider interface. `JinaProvider` is the v1 implementation, but the image downloading, link rewriting, and file output logic contain no Jina-specific code. See [`DESIGN.md`](DESIGN.md) for details.

## Testing approach

- All HTTP interactions are mocked via the [`responses`](https://github.com/getsentry/responses) library
- Filesystem tests use pytest's `tmp_path` fixture
- Test IDs map to acceptance criteria in `REQUIREMENTS.md` (T-01 through T-28, plus additional edge cases)
- Integration tests (I-01 through I-05) are run manually against real URLs — see `docs/integration-test-results.md`

## Submitting changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Ensure all tests pass and lint is clean
4. Open a pull request with a clear description of what and why
