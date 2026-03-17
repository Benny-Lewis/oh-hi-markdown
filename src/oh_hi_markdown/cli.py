"""CLI entry point for oh-hi-markdown."""

import argparse
import ipaddress
import sys
from pathlib import Path
from urllib.parse import urlparse

from oh_hi_markdown.config import VERSION
from oh_hi_markdown.exceptions import FilesystemError, ProviderError
from oh_hi_markdown.jina import JinaProvider
from oh_hi_markdown.pipeline import run


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


def validate_url(url: str) -> str | None:
    """Return an error message when the URL violates v1 input rules."""
    parsed = urlparse(url)

    if parsed.scheme.lower() not in {"http", "https"}:
        return "URL must start with http:// or https://"

    if not parsed.hostname:
        return "URL must include a non-empty host"

    hostname = parsed.hostname.lower()
    if hostname == "localhost":
        return "Localhost URLs are not allowed"

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return None

    # Unwrap IPv4-mapped IPv6 addresses (e.g., ::ffff:192.168.1.1)
    if hasattr(address, "ipv4_mapped") and address.ipv4_mapped is not None:
        address = address.ipv4_mapped

    if address.is_loopback:
        return "Loopback IP URLs are not allowed"

    if address.is_private:
        return "Private IP URLs are not allowed"

    if address.is_link_local:
        return "Link-local IP URLs are not allowed"

    return None


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.url is None:
        parser.print_help()
        sys.exit(1)

    validation_error = validate_url(args.url)
    if validation_error is not None:
        print(f"Error: {validation_error}", file=sys.stderr)
        sys.exit(1)

    provider = JinaProvider()
    output_dir = Path(args.output)

    try:
        result = run(
            url=args.url,
            output_dir=output_dir,
            force=args.force,
            provider=provider,
        )
    except ProviderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except FilesystemError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(3)
    except Exception as exc:
        print(f"Error: Unexpected error: {exc}", file=sys.stderr)
        sys.exit(4)

    if result.images_found > 0:
        print(
            f"{result.outcome}: {result.images_downloaded}/{result.images_found} images downloaded"
        )
    print(f"Saved to {result.output_path}")
    sys.exit(0)
