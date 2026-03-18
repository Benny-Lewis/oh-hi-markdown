# oh-hi-markdown (ohmd)

CLI tool that downloads web articles as AI-friendly markdown with local images via Jina Reader API.

## Quick Reference

- `pip install -e .` — install in dev mode
- `python -m pytest --tb=short -q` — run tests (32 unit tests, ~0.7s)
- `ruff check && ruff format --check` — lint
- `ohmd <url> -o <dir>` — run the tool
- `JINA_API_KEY` env var is optional; without it, no AI-generated alt text

## Architecture

Pipeline: URL → `jina.py` (fetch) → `parser.py` (extract images) → `images.py` (download) → `writer.py` (article.md) → `publisher.py` (atomic publish)

Key files: `src/oh_hi_markdown/{cli,jina,parser,images,writer,publisher,pipeline,log}.py`

## Testing

- All HTTP mocked via `responses` library (`@responses.activate`)
- Filesystem tests use pytest `tmp_path`
- Test IDs map to acceptance criteria in `docs/superpowers/specs/2026-03-14-test-strategy-design.md`
- Integration test results in `docs/integration-test-results.md`

## Gotchas

- `X-With-Generated-Alt: true` header requires a valid Jina API key — only sent when `JINA_API_KEY` is set
- Many CDNs serve images as `application/octet-stream` — code falls back to URL extension check
- Jina returns HTTP 451 for some news sites (legal restrictions)
- Some sites return soft 404s (200 with error page content) — Jina passes these through

## Project Status

See PLAN.md for lifecycle (steps 1-8 complete, steps 9-10 remain: docs + release tag).
See BACKLOG.md for v2+ ideas.
