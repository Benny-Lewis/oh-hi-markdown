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
