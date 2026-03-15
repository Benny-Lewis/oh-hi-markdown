"""Writer module tests: slug generation, title fallback, front matter."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 3")
def test_t13_title_with_special_characters():
    """T-13: Article title with special characters: slug is properly sanitized,
    folder created with correct name."""


@pytest.mark.skip(reason="Not yet implemented — slice 3")
def test_t14_title_empty_or_missing():
    """T-14: Article title is empty or missing: fallback naming applied
    per metadata fallback rules."""


@pytest.mark.skip(reason="Not yet implemented — slice 3")
def test_t25_front_matter_field_order_and_omission():
    """T-25: Front matter field order and omission: optional fields missing
    from Jina response are omitted (not blank), required fields present,
    field order matches spec."""
