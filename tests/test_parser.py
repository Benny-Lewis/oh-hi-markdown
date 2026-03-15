"""Parser module tests: image extraction edge cases."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 6")
def test_t16_data_uri_ignored():
    """T-16: Image with data: URI in markdown: left unmodified,
    not downloaded, not counted in summary."""


@pytest.mark.skip(reason="Not yet implemented — slice 5")
def test_t17_empty_alt_text():
    """T-17: Markdown with empty alt text ![](url): image downloaded,
    empty alt preserved in output."""


@pytest.mark.skip(reason="Not yet implemented — slice 13")
def test_t22_parentheses_in_url():
    """T-22: Image URL containing parentheses or syntax that challenges
    the regex parser. Either processed correctly or left completely unmodified."""
