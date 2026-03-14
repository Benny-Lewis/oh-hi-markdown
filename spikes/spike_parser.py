#!/usr/bin/env python3
"""
Spike 1: Validate IMAGE_PATTERN regex against real Jina Reader API output.

Run this script locally (not in a sandboxed environment) to fetch real
markdown from Jina Reader and test the regex against it.

Usage:
    python spikes/spike_parser.py

Requirements:
    - requests (pip install requests)
    - Unrestricted internet access to r.jina.ai
"""

import re
import json
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\(([^)]+)\)', re.DOTALL)

TEST_URLS = [
    "https://en.wikipedia.org/wiki/Golden_Gate_Bridge",
    "https://arstechnica.com/science/2024/03/the-discovery-of-high-temperature-superconductors/",
    "https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout",
    "https://www.bbc.com/news/science-environment-68123456",
    "https://github.com/anthropics/anthropic-cookbook",
    "https://docs.python.org/3/library/re.html",
]


def fetch_jina(url: str, retries: int = 2) -> str | None:
    """Fetch markdown content for a URL via Jina Reader API."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"Accept": "application/json"}

    for attempt in range(retries + 1):
        try:
            resp = requests.get(jina_url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("data", {}).get("content", "")
                if content:
                    return content
                else:
                    print(f"    Warning: Empty content for {url}")
                    return None
            elif resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"    HTTP {resp.status_code} for {url}")
                return None
        except requests.RequestException as e:
            print(f"    Request error: {e}")
            if attempt < retries:
                time.sleep(2)
                continue
            return None
    return None


def analyze_content(content: str, source: str) -> dict:
    """Run the regex against markdown content and report findings."""
    matches = IMAGE_PATTERN.findall(content)

    result = {
        "source": source,
        "total_images": len(matches),
        "images": [],
        "data_uris": 0,
        "multi_line_alt": 0,
        "urls_with_query_params": 0,
        "urls_with_fragments": 0,
        "empty_alt": 0,
        "html_img_tags": 0,
        "html_img_tags_list": [],
        "reference_style_images": 0,
        "false_positives_in_code_blocks": 0,
    }

    for alt, url in matches:
        img = {
            "alt": (alt[:80] + "...") if len(alt) > 80 else alt,
            "url": (url[:120] + "...") if len(url) > 120 else url,
        }
        result["images"].append(img)

        if url.startswith("data:"):
            result["data_uris"] += 1
        if "\n" in alt:
            result["multi_line_alt"] += 1
        if "?" in url:
            result["urls_with_query_params"] += 1
        if "#" in url:
            result["urls_with_fragments"] += 1
        if alt.strip() == "":
            result["empty_alt"] += 1

    # Detect HTML <img> tags the regex misses
    html_imgs = re.findall(r'<img\s[^>]*src=["\']([^"\']+)["\'][^>]*/?\s*>', content, re.IGNORECASE)
    result["html_img_tags"] = len(html_imgs)
    result["html_img_tags_list"] = html_imgs[:10]  # cap for readability

    # Detect reference-style images
    ref_imgs = re.findall(r'!\[([^\]]*)\]\[([^\]]+)\]', content)
    result["reference_style_images"] = len(ref_imgs)

    # Detect false positives inside code blocks
    code_blocks = re.findall(r'```[\s\S]*?```', content)
    for block in code_blocks:
        fps = IMAGE_PATTERN.findall(block)
        result["false_positives_in_code_blocks"] += len(fps)

    return result


def run_edge_case_tests():
    """Test specific known edge cases."""
    print("\n" + "=" * 70)
    print("Edge Case Tests (synthetic)")
    print("=" * 70)

    # 1. Parenthesized URL
    test1 = '![Map](https://example.com/SF_Bay_Area_(map).png)'
    m = IMAGE_PATTERN.search(test1)
    if m:
        _, url = m.groups()
        expected = "https://example.com/SF_Bay_Area_(map).png"
        if url != expected:
            print(f"\n1. Parenthesized URL: CONFIRMED LIMITATION")
            print(f"   Input:    {test1}")
            print(f"   Got URL:  {url}")
            print(f"   Expected: {expected}")
        else:
            print(f"\n1. Parenthesized URL: Matched correctly (unexpected)")

    # 2. Nested image-link
    test2 = '[![thumb](https://example.com/thumb.png)](https://example.com/full.png)'
    matches = IMAGE_PATTERN.findall(test2)
    print(f"\n2. Nested image-link: [![alt](img)](link)")
    print(f"   Input: {test2}")
    for alt, url in matches:
        print(f"   Match: alt='{alt}', url='{url}'")

    # 3. Multi-line alt text
    test3 = '![This is a very long caption\nthat spans multiple lines\nfor testing](https://example.com/img.png)'
    m = IMAGE_PATTERN.search(test3)
    if m:
        alt, url = m.groups()
        print(f"\n3. Multi-line alt text: MATCHED OK")
        print(f"   Alt lines: {alt.count(chr(10)) + 1}")
    else:
        print(f"\n3. Multi-line alt text: FAILED TO MATCH")

    # 4. Data URI
    test4 = '![icon](data:image/png;base64,iVBORw0KGgo=)'
    m = IMAGE_PATTERN.search(test4)
    if m:
        _, url = m.groups()
        print(f"\n4. Data URI: Matched (url starts with 'data:'={url.startswith('data:')})")
        print(f"   Post-extraction filter needed: YES")

    # 5. Empty alt text
    test5 = '![](https://example.com/img.png)'
    m = IMAGE_PATTERN.search(test5)
    if m:
        alt, url = m.groups()
        print(f"\n5. Empty alt text: MATCHED OK (alt='{alt}')")


def main():
    print("=" * 70)
    print("Spike 1: IMAGE_PATTERN Regex Validation Against Jina Reader Output")
    print("=" * 70)
    print()
    print(f"Regex: IMAGE_PATTERN = re.compile(r'!\\[(.*?)\\]\\(([^)]+)\\)', re.DOTALL)")
    print()

    all_results = []
    fetched_content = {}

    for url in TEST_URLS:
        print(f"Fetching: {url}")
        content = fetch_jina(url)

        if content is None:
            print(f"  SKIPPED (fetch failed)\n")
            continue

        fetched_content[url] = content
        print(f"  Content length: {len(content)} chars")

        result = analyze_content(content, url)
        all_results.append(result)

        print(f"  Images found: {result['total_images']}")
        if result["data_uris"]:
            print(f"  Data URIs: {result['data_uris']}")
        if result["html_img_tags"]:
            print(f"  HTML <img> tags (MISSED by regex): {result['html_img_tags']}")
            for src in result["html_img_tags_list"][:3]:
                print(f"    - {src[:100]}")
        if result["multi_line_alt"]:
            print(f"  Multi-line alt texts: {result['multi_line_alt']}")
        if result["urls_with_query_params"]:
            print(f"  URLs with query params: {result['urls_with_query_params']}")
        if result["urls_with_fragments"]:
            print(f"  URLs with fragments: {result['urls_with_fragments']}")
        if result["empty_alt"]:
            print(f"  Empty alt texts: {result['empty_alt']}")
        if result["reference_style_images"]:
            print(f"  Reference-style images (MISSED): {result['reference_style_images']}")
        if result["false_positives_in_code_blocks"]:
            print(f"  FALSE POSITIVES in code blocks: {result['false_positives_in_code_blocks']}")

        # Show first few images for inspection
        print(f"  Sample images:")
        for img in result["images"][:5]:
            alt_preview = img["alt"][:50].replace("\n", "\\n")
            print(f"    ![{alt_preview}]({img['url'][:80]})")
        if len(result["images"]) > 5:
            print(f"    ... and {len(result['images']) - 5} more")
        print()

        # Rate limit courtesy
        time.sleep(2)

    # Edge case tests (always run, no network needed)
    run_edge_case_tests()

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    if not all_results:
        print("\n  No URLs were successfully fetched.")
        print("  Edge case tests above still validate regex behavior.")
        print("  To test with real data, run this script on a machine with")
        print("  unrestricted internet access.")
    else:
        total_images = sum(r["total_images"] for r in all_results)
        total_html = sum(r["html_img_tags"] for r in all_results)
        total_multiline = sum(r["multi_line_alt"] for r in all_results)
        total_query = sum(r["urls_with_query_params"] for r in all_results)
        total_data = sum(r["data_uris"] for r in all_results)
        total_empty = sum(r["empty_alt"] for r in all_results)
        total_ref = sum(r["reference_style_images"] for r in all_results)
        total_fp = sum(r["false_positives_in_code_blocks"] for r in all_results)

        print(f"\n  URLs tested: {len(all_results)}")
        print(f"  Total markdown images matched: {total_images}")
        print(f"  HTML <img> tags missed: {total_html}")
        print(f"  Multi-line alt texts (matched OK): {total_multiline}")
        print(f"  URLs with query params (matched OK): {total_query}")
        print(f"  Data URIs (matched, need post-filter): {total_data}")
        print(f"  Empty alt texts (matched OK): {total_empty}")
        print(f"  Reference-style images (missed): {total_ref}")
        print(f"  False positives (code blocks): {total_fp}")

    # Save raw data
    output = {
        "results": all_results,
        "fetched_urls": list(fetched_content.keys()),
        "failed_urls": [u for u in TEST_URLS if u not in fetched_content],
    }
    output_path = "spikes/spike1_raw_data.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Raw data saved to {output_path}")


if __name__ == "__main__":
    main()
