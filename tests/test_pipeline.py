"""Pipeline end-to-end tests (mocked HTTP)."""

import pytest


@pytest.mark.skip(reason="Not yet implemented — slice 5")
def test_t01_standard_article_with_images():
    """T-01: Standard article with 3 images: all download successfully,
    all links rewritten to local paths, front matter complete with correct field order."""


@pytest.mark.skip(reason="Not yet implemented — slice 4")
def test_t02_article_with_no_images():
    """T-02: Article with no images: article.md created, no images/ folder,
    run reports 'Success.'"""
