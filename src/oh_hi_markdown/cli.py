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
