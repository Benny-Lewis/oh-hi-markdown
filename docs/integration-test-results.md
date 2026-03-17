# Integration Test Results

**Date:** 2026-03-17
**Branch:** `test/integration-manual`
**Tool version:** ohmd v0.1.0
**API key:** None (tested without `JINA_API_KEY`)

---

## Summary

| ID | Result | Images | URL |
|----|--------|--------|-----|
| I-01 | PASS | 6/6 | GitHub engineering blog |
| I-02 | PASS | 301/301 | Wikipedia (2024 Summer Olympics) |
| I-03 | PASS | 16/16 | GitHub Docs (PR review guide) |
| I-04 | PASS | 81/81 | Wikipedia (Hubble Space Telescope) |
| I-05 | PASS (partial) | 47/47 | Medium (Python data viz tutorial) |

**Bugs found:** 2 (both fixed in this branch)

---

## I-01: Tech blog with mixed image types (PNG, JPG, SVG)

**URL:** `https://github.blog/engineering/architecture-optimization/githubs-engineering-fundamentals-program-how-we-deliver-on-availability-security-and-accessibility/`

**What it exercises:**
- Mixed image types: 1 PNG, 1 JPG, 4 SVGs
- Query parameters in image URLs (`?w=1024&resize=1109%2C524`)
- Images from multiple domains (`github.blog`, `avatars.githubusercontent.com`)
- Front matter extraction (title, author, date, description all populated)

**Result:** PASS — 6/6 images downloaded. All three image types saved correctly. Query parameters stripped from filenames. Front matter complete with author and date.

**Output folder:** `githubs-engineering-fundamentals-program-how-we-deliver-on-availability/`

---

## I-02: News article with hero image and inline photos

**URL:** `https://en.wikipedia.org/wiki/2024_Summer_Olympics`

**What it exercises:**
- Large article with extensive inline images (301 total)
- Image count warning triggered (threshold: 50)
- Mix of JPG, PNG, SVG formats
- URL-encoded characters in image URLs (parentheses, percent-encoding)
- Filename collision disambiguation (multiple images from same paths)

**Result:** PASS — 301/301 images downloaded. The `⚠ Article references 301 unique images (threshold: 50)` warning fired correctly. All images saved, filenames disambiguated where needed.

**Output folder:** `2024-summer-olympics/`

**Notes:** Originally attempted BBC and The Verge articles, but both returned soft 404s through Jina. Wikipedia proved to be a reliable, image-rich source for this test.

---

## I-03: Documentation page with diagrams and code screenshots

**URL:** `https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request`

**What it exercises:**
- Technical documentation with UI screenshots
- All PNG format images served from `docs.github.com/assets/`
- Descriptive filenames derived from URL paths
- Clean markdown structure without boilerplate

**Result:** PASS — 16/16 screenshots downloaded. All images are clear UI screenshots with descriptive filenames (`repo-tabs-pull-requests-global-nav-update.png`, `diff-settings-menu.png`, etc.). Article markdown well-structured.

**Output folder:** `reviewing-proposed-changes-in-a-pull-request-github-docs/`

---

## I-04: Article with many images (10+)

**URL:** `https://en.wikipedia.org/wiki/Hubble_Space_Telescope`

**What it exercises:**
- 81 images (well above the 50-image warning threshold)
- Mix of JPG, PNG, SVG, JPEG, GIF formats
- Animated GIF download (orbit trajectory animation, 2MB)
- Thumbnail images at various sizes (20px, 40px, 120px, 250px, 500px)
- URL-encoded parentheses and special characters
- Images served from multiple Wikimedia subdomains

**Result:** PASS — 81/81 images downloaded. Warning `⚠ Article references 81 unique images (threshold: 50)` fired correctly. All image types including animated GIF saved successfully.

**Output folder:** `hubble-space-telescope/`

---

## I-05: Article where some images are hotlink-protected

**URL:** `https://medium.com/codex/step-by-step-guide-to-data-visualizations-in-python-b322129a1540`

**What it exercises:**
- Medium article (platform known for image access controls)
- 47 images including PNG, JPG, WebP, and animated GIF
- Images served from `miro.medium.com` CDN with various resize/format parameters
- Filename collision disambiguation (same base filename at different sizes, e.g., `-a`, `-b`, `-c` suffixes)
- Mixed format delivery (some images served as WebP via format parameter)

**Result:** PASS — 47/47 images downloaded. Medium's CDN (`miro.medium.com`) does not enforce hotlink protection on direct image requests. The `Referer` header (set to article URL per spec) likely helped. Filename collision disambiguation worked correctly across multiple sizes of the same base image.

**Notes on hotlink protection:** True hotlink protection (403 on direct image fetch) proved difficult to find in practice. Most CDNs serve images to any requester with the correct URL. Our `Referer` header (D-9) further reduces the chance of rejection. The graceful degradation path (failed images keep original URLs, warnings logged) is thoroughly covered by unit tests T-07 and T-19.

**Output folder:** `a-step-by-step-guide-to-data-visualizations-in-python/`

---

## Bugs Found and Fixed

### Bug 1: `X-With-Generated-Alt` header sent without API key

**File:** `src/oh_hi_markdown/jina.py`
**Severity:** Critical — tool completely unusable without a valid Jina API key

**Problem:** The `X-With-Generated-Alt: true` header was always sent in Jina API requests. Jina now requires a valid API key for this feature, returning HTTP 401 even for free-tier requests when this header is present.

**Fix:** Only send `X-With-Generated-Alt: true` when an API key is configured. Without a key, the tool works normally — images just use their existing alt text instead of AI-generated descriptions.

### Bug 2: `application/octet-stream` Content-Type rejected

**File:** `src/oh_hi_markdown/images.py`
**Severity:** Medium — affects images served by CDNs that don't set proper Content-Type

**Problem:** The Content-Type validation rejected any non-`image/*` Content-Type. Many CDNs (notably Google Cloud Storage) serve image files (especially WebP) with `Content-Type: application/octet-stream`.

**Fix:** When Content-Type is `application/octet-stream`, fall back to URL extension checking (same logic as no Content-Type header). Images with known extensions (`.png`, `.jpg`, `.webp`, etc.) are accepted; others are still rejected.

---

## Test Environment

- **OS:** Windows 11 Pro (10.0.22631)
- **Python:** 3.x (via pip install -e .)
- **Network:** Direct internet, no proxy
- **API key:** Not used (tested free-tier Jina access)
- **All 29 unit tests:** Passing before and after fixes
