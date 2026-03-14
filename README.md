# oh-hi-markdown

> A CLI tool that downloads web articles as clean, AI-friendly markdown with locally-stored images.

**Status:** Pre-development — requirements locked, design phase next.

## What it will do

- Fetch a web article and extract clean markdown (via Jina Reader)
- Download all images to a local folder
- Rewrite image references to use local paths
- Include AI-generated image captions
- Output a self-contained folder ready for AI ingestion

## Commands

```bash
ohmd https://example.com/some-article
ohhimark https://example.com/some-article   # same thing
```

## Project docs

- [`REQUIREMENTS.md`](REQUIREMENTS.md) — v1 specification (locked)
- [`DESIGN.md`](DESIGN.md) — technical design document
- [`PLAN.md`](PLAN.md) — development lifecycle plan

## License

[MPL-2.0](LICENSE)
