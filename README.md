# oh-hi-markdown

> CLI tool that downloads web articles as AI-friendly markdown with locally stored images.

Extracts clean article content from any URL using [Jina Reader](https://jina.ai/reader/), downloads all images locally, rewrites markdown image references to relative paths, and packages everything into a self-contained folder ready for AI workflows.

## Install

Requires Python 3.10+.

```bash
pip install git+https://github.com/Benny-Lewis/oh-hi-markdown.git
```

For local development:

```bash
git clone https://github.com/Benny-Lewis/oh-hi-markdown.git
cd oh-hi-markdown
pip install -e ".[dev]"
```

Both `ohmd` and `ohhimark` commands are installed — they're identical.

## Usage

```bash
# Download an article to the current directory
ohmd https://example.com/some-article

# Specify an output directory
ohmd https://example.com/some-article -o ~/articles

# Overwrite if the output folder already exists
ohmd https://example.com/some-article --force

# Both commands are identical
ohhimark https://example.com/some-article
```

### Output structure

```
./how-nuclear-batteries-work-a-deep-dive/
├── article.md          # Article content with local image references
├── images/             # Downloaded images (only if images were found)
│   ├── 001-reactor-diagram.png
│   ├── 002-power-output-chart.jpg
│   └── 003-comparison-table.png
└── ohmd.log            # Detailed log of the download operation
```

The folder name is derived from the article title (slugified to lowercase with hyphens). `article.md` includes YAML front matter with metadata:

```yaml
---
title: "How Nuclear Batteries Work: A Deep Dive"
author: "Jane Smith"
date: "2026-03-10"
source_url: "https://example.com/how-nuclear-batteries-work-a-deep-dive"
description: "An exploration of radioisotope thermoelectric generators."
downloaded: "2026-03-13T14:30:00Z"
tool: "ohmd v0.1.0"
---
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `JINA_API_KEY` | No | Jina Reader API key for higher rate limits and AI-generated image alt text. Free keys available at [jina.ai](https://jina.ai) (no credit card required). |

```bash
export JINA_API_KEY=jina_your_key_here
ohmd https://example.com/some-article
```

Without an API key, Jina imposes lower rate limits. If you hit HTTP 429 errors, setting a key will resolve it. When a key is set, the tool also requests AI-generated image descriptions via Jina's `X-With-Generated-Alt` feature.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success or partial success — article saved (some image downloads may have failed). |
| `1` | Invalid input — bad URL, missing arguments, or private/localhost IP. |
| `2` | Article extraction failed — Jina error, rate limit, or empty response. |
| `3` | Filesystem conflict or write failure — folder exists without `--force`, permissions error. |
| `4` | Unexpected internal error. |

## How it works

1. **Fetch** — Sends the URL to [Jina Reader](https://jina.ai/reader/) (`r.jina.ai`), which renders the page, strips navigation/ads/boilerplate, and returns clean markdown. If `JINA_API_KEY` is set, requests AI-generated image alt text.
2. **Parse** — Extracts all `![alt](url)` image references from the markdown.
3. **Download** — Fetches each image sequentially with a 30-second timeout and up to 3 retries (exponential backoff). Sets the `Referer` header to the article URL for hotlink-protected images.
4. **Rewrite** — Replaces remote image URLs with relative local paths (`./images/001-name.ext`). Failed images keep their original remote URLs.
5. **Publish** — Writes all output to a temporary directory first, then atomically renames it to the final path. If `--force` is used and the folder exists, the old folder is backed up and only replaced after the new output is fully written.

## Privacy and data

- **URLs are sent to Jina Reader.** When you run `ohmd <url>`, the URL is submitted to Jina's hosted API at `r.jina.ai` for content extraction. Jina processes the target page on their infrastructure.
- **Referer header on image requests.** Image download requests include a `Referer` header set to the original article URL. This improves compatibility with hotlink-protected images but means the target image server sees which article URL triggered the download.
- **API key handling.** If set, `JINA_API_KEY` is sent as a Bearer token to Jina. It is never written to log files or console output.
- **No telemetry.** The tool does not phone home or collect usage data beyond the Jina API call required for content extraction.

## Known limitations

- **Single URL per invocation.** Use a shell loop for batch processing: `for url in $(cat urls.txt); do ohmd "$url"; done`
- **No paywall or authentication support.** Login-gated content is not supported.
- **Rate limits without API key.** Jina imposes lower rate limits without a `JINA_API_KEY`. If you hit HTTP 429, [get a free key](https://jina.ai).
- **Some sites return HTTP 451.** Jina cannot access content restricted for legal reasons.
- **Windows support is best-effort.** Tested on macOS and Linux. Atomic rename behavior is not guaranteed on Windows.
- **HTML `<img>` tags are best-effort.** The parser targets standard markdown image syntax (`![alt](url)`). HTML image tags in Jina's output may not be processed.
- **No image size limits enforced.** Warnings are emitted for images over 10 MB, total downloads over 50 MB, or more than 50 images, but downloads are not blocked.

## Development

```bash
# Run tests (32 unit tests, ~0.7s)
python -m pytest --tb=short -q

# Lint
ruff check && ruff format --check
```

## Documentation

- [`REQUIREMENTS.md`](REQUIREMENTS.md) — Full v1 specification
- [`DESIGN.md`](DESIGN.md) — Technical design document
- [`BACKLOG.md`](BACKLOG.md) — Future plans and v2+ ideas

## License

[MPL-2.0](LICENSE)
