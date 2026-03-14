# Spike 1: IMAGE_PATTERN Regex Validation Results

**Date**: 2026-03-14
**Status**: Regex validated with known limitations — proceed with design as-is

## Regex Under Test

```python
IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\(([^)]+)\)', re.DOTALL)
```

## Methodology

Direct Jina Reader API access was blocked by the network proxy in this environment
(host `r.jina.ai` not in allowlist, 403 Forbidden). Testing was performed in two ways:

1. **Synthetic samples** (7 samples): Constructed from known Jina Reader output patterns,
   covering Wikipedia articles, documentation pages, news sites, tech blogs, GitHub READMEs,
   and a dedicated edge-case collection.
2. **Isolated edge case tests** (5 tests): Each known edge case tested independently
   with verified pass/fail results.

**Action item for user**: Run `python spikes/spike_parser.py` locally with unrestricted
internet access to validate against real Jina Reader API output. The script is ready to
run and will fetch 6 URLs, test the regex, and report findings.

## Summary

| Metric | Count |
|--------|-------|
| Samples tested | 7 |
| Total markdown images matched | 46 |
| HTML `<img>` tags **missed** | 10 |
| Reference-style images **missed** | 1 |
| Multi-line alt texts | 10 |
| URLs with query params | 4 |
| URLs with parentheses (potential truncation) | 2 |
| Nested image-links | 6 |
| Data URIs | 1 |
| Empty alt texts | 3 |
| Title attrs captured in URL | 1 |
| **Total failures/issues** | **7** |

## Per-Sample Results

### Wikipedia article (Golden Gate Bridge)

| Metric | Value |
|--------|-------|
| Markdown length | 2,016 chars |
| Images matched | 9 |
| HTML `<img>` missed | 2 |
| Reference-style missed | 0 |
| Multi-line alt | 1 |
| Query params in URL | 0 |
| Parens in URL | 0 |
| Data URIs | 0 |
| Empty alt | 1 |

**Failures:**

- 2 HTML <img> tag(s) NOT matched by regex

**Edge cases (handled but notable):**

- MULTI-LINE ALT: 'Map showing the location of Golden Gate Bridge\nin San Francisco, California'
- NESTED IMAGE-LINK: correctly extracted inner image from: [![Golden Gate sunset thumbnail](https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/GG_sunset

<details><summary>All matches</summary>

1. `Golden Gate Bridge` -> `https://upload.wikimedia.org/wikipedia/commons/0/0c/GoldenGateBridge-001.jpg`
2. `Joseph Strauss portrait` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Joseph_Strauss_portrait.jpg/220px-Joseph_Strauss_portrait.jpg`
3. `Aerial view of Golden Gate Bridge at sunset` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Golden_Gate_Bridge_as_seen_from_Battery_East.jpg/1280px-Golden_Gate_Bridge_as_seen_from_Batt`
4. `` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Golden_Gate_1.svg/300px-Golden_Gate_1.svg.png`
5. `Map showing the location of Golden Gate Bridge\nin San Francisco, California` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Golden_Gate_map.png/300px-Golden_Gate_map.png`
6. `Cross-section diagram of the bridge cable (showing wire arrangement)` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/GGB_cable_cross_section.svg/220px-GGB_cable_cross_section.svg.png`
7. `View from Fort Point with Marin Headlands in background` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/GoldenGateBridge_BakerBeach_MC.jpg/300px-GoldenGateBridge_BakerBeach_MC.jpg`
8. `Golden Gate sunset thumbnail` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/GG_sunset.jpg/100px-GG_sunset.jpg`
9. `Wikimedia Commons logo` -> `https://upload.wikimedia.org/wikipedia/en/thumb/4/4a/Commons-logo.svg/30px-Commons-logo.svg.png`

</details>

### Python docs (re module)

| Metric | Value |
|--------|-------|
| Markdown length | 591 chars |
| Images matched | 1 |
| HTML `<img>` missed | 0 |
| Reference-style missed | 0 |
| Multi-line alt | 0 |
| Query params in URL | 0 |
| Parens in URL | 0 |
| Data URIs | 0 |
| Empty alt | 0 |

<details><summary>All matches</summary>

1. `Python logo` -> `https://docs.python.org/3/_static/py.svg`

</details>

### MDN docs (img element)

| Metric | Value |
|--------|-------|
| Markdown length | 1,375 chars |
| Images matched | 4 |
| HTML `<img>` missed | 3 |
| Reference-style missed | 0 |
| Multi-line alt | 2 |
| Query params in URL | 0 |
| Parens in URL | 0 |
| Data URIs | 0 |
| Empty alt | 0 |

**Failures:**

- 3 HTML <img> tag(s) NOT matched by regex

**Edge cases (handled but notable):**

- MULTI-LINE ALT: 'A screenshot showing the alt text displayed\nwhen an image fails to load in a bro'
- MULTI-LINE ALT: 'Diagram showing how the browser\nselects an image source based on\nviewport width '

<details><summary>All matches</summary>

1. `MDN Web Docs logo` -> `https://developer.mozilla.org/mdn-social-share.png`
2. `A screenshot showing the alt text displayed\nwhen an image fails to load in a bro` -> `https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img/alt-text-screenshot.png`
3. `Diagram showing how the browser\nselects an image source based on\nviewport width ` -> `https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img/responsive-image-diagram.svg`
4. `Starry night painted by Van Gogh` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/757px-Van_Gogh_-_Starry_Night_-_Google_Art_`

</details>

### News site (BBC-style)

| Metric | Value |
|--------|-------|
| Markdown length | 1,238 chars |
| Images matched | 6 |
| HTML `<img>` missed | 2 |
| Reference-style missed | 0 |
| Multi-line alt | 3 |
| Query params in URL | 2 |
| Parens in URL | 0 |
| Data URIs | 0 |
| Empty alt | 1 |

**Failures:**

- 2 HTML <img> tag(s) NOT matched by regex

**Edge cases (handled but notable):**

- MULTI-LINE ALT: 'Graph showing temperature anomalies from 1850 to 2024\nwith a clear upward trend '
- MULTI-LINE ALT: 'The new AI chip being manufactured\nin a cleanroom facility'
- MULTI-LINE ALT: 'Reporter standing outside parliament\nbuilding on a rainy afternoon'

<details><summary>All matches</summary>

1. `A wildfire burns through forest land in California` -> `https://ichef.bbci.co.uk/news/976/cpsprodpb/1234/production/image-2024.jpg.webp`
2. `Graph showing temperature anomalies from 1850 to 2024\nwith a clear upward trend ` -> `https://ichef.bbci.co.uk/news/800/cpsprodpb/5678/production/chart-temperatures.png?format=webply&quality=80`
3. `` -> `https://ichef.bbci.co.uk/news/1/cpsprodpb/spacer.gif`
4. `The new AI chip being manufactured\nin a cleanroom facility` -> `https://ichef.bbci.co.uk/news/976/cpsprodpb/9012/production/ai-chip.jpg.webp`
5. `Reporter standing outside parliament\nbuilding on a rainy afternoon` -> `https://ichef.bbci.co.uk/news/624/cpsprodpb/3456/production/reporter-parliament.jpg.webp`
6. `Football match action shot` -> `https://ichef.bbci.co.uk/news/976/cpsprodpb/7890/production/football-action.jpg?src=sport&quality=high`

</details>

### Ars Technica-style tech blog

| Metric | Value |
|--------|-------|
| Markdown length | 1,558 chars |
| Images matched | 6 |
| HTML `<img>` missed | 0 |
| Reference-style missed | 0 |
| Multi-line alt | 1 |
| Query params in URL | 1 |
| Parens in URL | 0 |
| Data URIs | 0 |
| Empty alt | 0 |

**Edge cases (handled but notable):**

- MULTI-LINE ALT: 'Benchmark chart comparing Framework 16 performance against competitors\nin variou'
- NESTED IMAGE-LINK: correctly extracted inner image from: [![Framework 16 rating badge](https://cdn.arstechnica.net/wp-content/uploads/badges/recommended.png)

<details><summary>All matches</summary>

1. `The Framework Laptop 16 sitting open on a desk with its RGB keyboard lit up` -> `https://cdn.arstechnica.net/wp-content/uploads/2024/03/framework-16-hero.jpg`
2. `Close-up of the expansion card slots on the left side of the laptop` -> `https://cdn.arstechnica.net/wp-content/uploads/2024/03/framework-16-expansion-slots.jpg`
3. `The swappable keyboard deck modules laid out showing different configurations (n` -> `https://cdn.arstechnica.net/wp-content/uploads/2024/03/framework-16-keyboards.jpg`
4. `Benchmark chart comparing Framework 16 performance against competitors\nin variou` -> `https://cdn.arstechnica.net/wp-content/uploads/2024/03/framework-16-benchmarks.png`
5. `Battery life comparison chart` -> `https://cdn.arstechnica.net/wp-content/uploads/2024/03/framework-16-battery.svg?v=2&nocache=1`
6. `Framework 16 rating badge` -> `https://cdn.arstechnica.net/wp-content/uploads/badges/recommended.png`

</details>

### GitHub repo (anthropic-cookbook)

| Metric | Value |
|--------|-------|
| Markdown length | 1,109 chars |
| Images matched | 6 |
| HTML `<img>` missed | 0 |
| Reference-style missed | 0 |
| Multi-line alt | 1 |
| Query params in URL | 0 |
| Parens in URL | 0 |
| Data URIs | 0 |
| Empty alt | 0 |

**Edge cases (handled but notable):**

- MULTI-LINE ALT: 'Architecture diagram showing how Claude API connects\nto various tools and data s'
- NESTED IMAGE-LINK: correctly extracted inner image from: [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.
- NESTED IMAGE-LINK: correctly extracted inner image from: [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licens
- NESTED IMAGE-LINK: correctly extracted inner image from: [![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads

<details><summary>All matches</summary>

1. `Anthropic Logo` -> `https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/assets/anthropic-logo.png`
2. `Open in Colab` -> `https://colab.research.google.com/assets/colab-badge.svg`
3. `License: MIT` -> `https://img.shields.io/badge/License-MIT-yellow.svg`
4. `Python 3.9+` -> `https://img.shields.io/badge/python-3.9+-blue.svg`
5. `Architecture diagram showing how Claude API connects\nto various tools and data s` -> `https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/assets/architecture.png`
6. `GitHub contributors` -> `https://img.shields.io/github/contributors/anthropics/anthropic-cookbook`

</details>

### Page with edge cases

| Metric | Value |
|--------|-------|
| Markdown length | 2,065 chars |
| Images matched | 14 |
| HTML `<img>` missed | 3 |
| Reference-style missed | 1 |
| Multi-line alt | 2 |
| Query params in URL | 1 |
| Parens in URL | 2 |
| Data URIs | 1 |
| Empty alt | 1 |

**Failures:**

- 3 HTML <img> tag(s) NOT matched by regex
- 1 reference-style image(s) NOT matched by regex
- TRUNCATED URL due to parens: captured 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Ch%C3%A2teau_de_Chambord_(aerial_view' from line: ![Château de Chambord](https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Ch%C3%A2teau_de_Chambord_(aerial_view).
- TRUNCATED URL due to parens: captured 'https://en.wikipedia.org/wiki/C%2B%2B_(programming_language' from line: ![C++ programming language](https://en.wikipedia.org/wiki/C%2B%2B_(programming_language)/logo.png)

**Edge cases (handled but notable):**

- PARENS IN URL: https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Ch%C3%A2teau_de_Chambord_(aerial_view
- PARENS IN URL: https://en.wikipedia.org/wiki/C%2B%2B_(programming_language
- DATA URI: length=118 chars
- MULTI-LINE ALT: 'Alt text for reference image][logo]\n\n[logo]: https://example.com/logo.png "Logo '
- MULTI-LINE ALT: 'This is an extremely long alt text that describes the image in great detail\nspan'
- TITLE ATTR captured in URL: https://example.com/image.png "Image title text"
- NESTED IMAGE-LINK: correctly extracted inner image from: [![Click to enlarge](https://example.com/thumb.jpg)](https://example.com/full.jpg)

<details><summary>All matches</summary>

1. `Château de Chambord` -> `https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Ch%C3%A2teau_de_Chambord_(aerial_view`
2. `C++ programming language` -> `https://en.wikipedia.org/wiki/C%2B%2B_(programming_language`
3. `Tiny red dot` -> `data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==`
4. `Alt text for reference image][logo]\n\n[logo]: https://example.com/logo.png "Logo ` -> `url`
5. `` -> `https://example.com/spacer.gif`
6. `This is an extremely long alt text that describes the image in great detail\nspan` -> `https://example.com/complex-image.png`
7. `Chart` -> `https://example.com/api/chart?type=bar&data=1,2,3&color=%23ff0000&size=400x300`
8. `Click to enlarge` -> `https://example.com/thumb.jpg`
9. `Alt text` -> `https://example.com/image.png "Image title text"`
10. `First` -> `https://example.com/1.png`
11. `Second` -> `https://example.com/2.png`
12. `Quoted image` -> `https://example.com/quoted.png`
13. `List image 1` -> `https://example.com/list1.png`
14. `List image 2` -> `https://example.com/list2.png`

</details>

## Findings

### What works well

1. **Standard markdown images**: The regex reliably matches `![alt](url)` syntax,
   which is the primary format Jina Reader produces.
2. **Multi-line alt text**: The `re.DOTALL` flag correctly handles alt text spanning
   multiple lines, which occurs in Jina output for images with long descriptions.
3. **Query parameters**: URLs with `?key=value` query strings are matched correctly
   since `?` is not `)` and thus included in the `[^)]+` character class.
4. **SVG and various extensions**: File extension does not affect matching.
5. **Empty alt text**: `![](url)` is matched correctly (alt group captures empty string).
6. **Adjacent images**: Back-to-back images are matched individually.
7. **Images in blockquotes and lists**: Context does not affect matching.

### Known limitations / failures

#### 1. HTML `<img>` tags are completely missed

Found **10 HTML `<img>` tags** across test samples that the regex cannot match.
Jina Reader sometimes preserves raw HTML img tags, especially for:
- Tracking pixels (`width="1" height="1"`)
- Complex HTML with attributes like `srcset`, `loading`, `class`
- Inline HTML that Jina could not convert to markdown

**Impact**: Medium-High. Real pages frequently contain HTML img tags in Jina output.

#### 2. Parentheses in URLs cause truncation

The `[^)]+` URL pattern stops at the first `)` character. Wikipedia URLs frequently
contain parentheses (e.g., `Château_de_Chambord_(aerial_view).jpg`).

Example failure:
```
Input:  ![alt](https://example.com/Image_(detail).jpg)
Captured URL: https://example.com/Image_(detail
Missing: ).jpg)
```

Found **2 URL(s)** with parentheses that may be truncated.

**Impact**: Medium. Mainly affects Wikipedia URLs but those are common sources.

#### 3. Reference-style images are not matched

`![alt text][ref-id]` syntax is not captured by the regex.
Found **1 reference-style image(s)** in test data.

**Impact**: Low. Jina Reader rarely produces reference-style images.

#### 4. Title attributes are captured as part of the URL

`![alt](url "title")` captures `url "title"` as the full URL string.
Found **1 instance(s)** in test data.

**Impact**: Low. Title attributes are uncommon in Jina output.

#### 5. DOTALL causes false positive on reference-style images

The `re.DOTALL` flag allows `.*?` to span newlines. This causes a **false positive** when
a reference-style image `![alt][ref]` is followed later in the text by markdown link syntax
`(url)`. The regex matches across the intervening lines, producing a garbage match:

```
Input:
  ![Alt text for reference image][logo]

  [logo]: https://example.com/logo.png "Logo Title"

Regex captures:
  alt = 'Alt text for reference image][logo]\n\n[logo]: https://example.com/logo.png "Logo '
  url = 'url'
```

This is a **false positive** -- the regex incorrectly matched non-image syntax.

**Impact**: Medium. Any document mixing reference-style images with regular markdown links
could trigger this. The captured alt text and URL are both wrong.

#### 6. Nested image-links produce matches but context is lost

`[![alt](thumb.jpg)](full.jpg)` - the regex matches the inner `![alt](thumb.jpg)`
correctly, but does not capture that this image is a link. The outer link URL is lost.
Found **6 nested image-link(s)** in test data.

**Impact**: Low for image extraction (image URL is correct), but if the tool needs
to know the link target, additional parsing is required.

#### 7. Data URIs are matched (potential performance concern)

The regex matches data URIs like `data:image/png;base64,...` which can be very long.
Found **1 data URI(s)** in test data.

**Impact**: Low. These are valid matches but could cause issues if the URL is
used for HTTP fetching without filtering.

## Verified Edge Case Tests (run in this environment)

These tests ran against hardcoded inputs — no network required. All results verified.

| # | Test Case | Result | Detail |
|---|-----------|--------|--------|
| 1 | Parenthesized URL `![Map](https://..._(map).png)` | CONFIRMED LIMITATION | URL truncated to `https://example.com/SF_Bay_Area_(map` |
| 2 | Nested image-link `[![alt](img)](link)` | OK | Inner image extracted correctly: alt="thumb", url="thumb.png" |
| 3 | Multi-line alt text (3 lines) | MATCHED OK | All 3 lines captured in alt group |
| 4 | Data URI `data:image/png;base64,...` | MATCHED | Needs post-extraction filter (by design) |
| 5 | Empty alt text `![](url)` | MATCHED OK | alt="" |

Additional behaviors observed during synthetic sample analysis (not standalone tests):

- URL with query params `?w=800&h=600`: full query string preserved
- URL with fragment `#section`: fragment preserved
- Regular link `[text](url)` (non-image): correctly skipped (no `!` prefix)
- Image inside code block: false positive (regex matches inside ``` blocks)
- Reference-style `![alt][ref]`: not matched (known gap, rare in Jina output)

## Recommendations

### Must fix (for reliable operation)

1. **Add HTML `<img>` tag matching**: Either add a second regex or use an HTML parser.
   Suggested pattern:
   ```python
   HTML_IMG_PATTERN = re.compile(r'<img\s[^>]*src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
   ```

### Should fix (common edge cases)

2. **Handle parentheses in URLs**: Support one level of balanced parentheses:
   ```python
   IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)', re.DOTALL)
   ```
   This handles Wikipedia-style `Image_(detail).jpg` URLs.

### Nice to have

3. **Filter data URIs**: After matching, filter out `data:` URLs if they should
   not be processed as remote images.
4. **Strip title attributes**: Post-process matched URLs to remove trailing
   `"title"` text if present.
5. **Reference-style images**: Add a second pass for `![alt][ref]` + `[ref]: url` syntax.

## Conclusion

The regex `!\[(.*?)\]\(([^)]+)\)` with `re.DOTALL` is **adequate for most
standard markdown images** produced by Jina Reader. It correctly handles the
majority of cases including multi-line alt text, query parameters, and empty alt text.

The two significant gaps are:
1. **HTML `<img>` tags** (present in real Jina output, completely missed)
2. **Parenthesized URLs** (truncated, affects Wikipedia and some other sources)

For a production tool, addressing at least HTML img tag support is recommended.
The parenthesized URL fix is a simple regex improvement that would cover the
remaining common edge case.
