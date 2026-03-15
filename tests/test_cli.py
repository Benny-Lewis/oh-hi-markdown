"""CLI entry point and URL validation tests."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 1")
def test_t10_invalid_url_no_scheme():
    """T-10: Invalid URL input (no scheme): exit code 1, no files created,
    no HTTP requests made."""


@pytest.mark.skip(reason="Not yet implemented — slice 1")
def test_t24_private_url_rejected():
    """T-24: Private/internal URL rejected: literal private IPs and localhost
    cause exit code 1, no requests made."""


@pytest.mark.skip(reason="Not yet implemented — slice 12")
def test_t28_command_alias_equivalence():
    """T-28: Command alias equivalence: both ohmd and ohhimark entry points
    are installed and produce identical behavior."""
