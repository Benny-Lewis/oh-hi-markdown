"""CLI entry point and URL validation tests."""

import pytest

from oh_hi_markdown.cli import validate_url


def test_t10_invalid_url_no_scheme():
    """T-10: Invalid URL input (no scheme): exit code 1, no files created,
    no HTTP requests made."""
    # Bare domain with no scheme must be rejected.
    error = validate_url("example.com")
    assert error is not None
    assert "http" in error.lower()

    # ftp:// is not an accepted scheme.
    error = validate_url("ftp://example.com/article")
    assert error is not None

    # Valid https URL must pass validation.
    assert validate_url("https://example.com/article") is None

    # Valid http URL must pass validation.
    assert validate_url("http://example.com/article") is None


def test_t24_private_url_rejected():
    """T-24: Private/internal URL rejected: literal private IPs and localhost
    cause exit code 1, no requests made."""
    # RFC1918 private IPs.
    assert validate_url("https://192.168.1.1/page") is not None
    assert validate_url("https://10.0.0.1/page") is not None
    assert validate_url("https://172.16.0.1/page") is not None

    # Localhost.
    assert validate_url("https://localhost/page") is not None

    # IPv4 loopback.
    assert validate_url("https://127.0.0.1/page") is not None

    # IPv6 loopback.
    assert validate_url("https://[::1]/page") is not None

    # Link-local.
    assert validate_url("https://169.254.1.1/page") is not None

    # IPv4-mapped IPv6 addresses (bypass protection).
    assert validate_url("https://[::ffff:192.168.1.1]/page") is not None
    assert validate_url("https://[::ffff:127.0.0.1]/page") is not None

    # Public IP must pass.
    assert validate_url("https://93.184.216.34/page") is None


@pytest.mark.skip(reason="Not yet implemented — slice 12")
def test_t28_command_alias_equivalence():
    """T-28: Command alias equivalence: both ohmd and ohhimark entry points
    are installed and produce identical behavior."""
