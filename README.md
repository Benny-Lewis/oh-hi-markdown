# oh-hi-markdown

> CLI tool for downloading web articles as clean, AI-friendly markdown with locally stored images.

**Status:** Project scaffold in place. Packaging and CLI entry points exist; article download is not implemented yet.

## Install

For local development:

```bash
pip install -e ".[dev]"
```

## Current commands

Check the installed version:

```bash
ohmd --version
ohhimark --version
```

The article-processing command surface exists, but it currently exits with a clear non-zero error until the pipeline is implemented:

```bash
ohmd https://example.com/some-article
ohhimark https://example.com/some-article
```

## Documentation

- [`REQUIREMENTS.md`](REQUIREMENTS.md): v1 specification
- [`DESIGN.md`](DESIGN.md): technical design document
- [`PLAN.md`](PLAN.md): development lifecycle plan

## License

MPL-2.0
