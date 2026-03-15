"""CLI entry point for oh-hi-markdown."""

import argparse
import ipaddress
import sys
from urllib.parse import urlparse

from oh_hi_markdown.config import VERSION

RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
IPV4_LINK_LOCAL_NETWORK = ipaddress.ip_network("169.254.0.0/16")
IPV4_LOOPBACK_NETWORK = ipaddress.ip_network("127.0.0.0/8")
IPV6_LOOPBACK_ADDRESS = ipaddress.ip_address("::1")


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

    if address == IPV6_LOOPBACK_ADDRESS or (
        address.version == 4 and address in IPV4_LOOPBACK_NETWORK
    ):
        return "Loopback IP URLs are not allowed"

    if address.version == 4 and address in IPV4_LINK_LOCAL_NETWORK:
        return "Link-local IP URLs are not allowed"

    if address.version == 4 and any(address in network for network in RFC1918_NETWORKS):
        return "Private IP URLs are not allowed"

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

    # TODO: implement pipeline call
    print(f"Error: ohmd {VERSION} is not implemented yet", file=sys.stderr)
    sys.exit(4)
