# Backlog

Future improvements, deferred items, and v2+ ideas. Roughly grouped by area, not strictly prioritized.

## Features

- **Own vision model integration** — Use Claude API (or similar) to generate richer image descriptions, replacing dependency on Jina's captioning.
- **Alt text quality assessment** — AI evaluates existing alt text; if low quality, enhance or supplement it; if good, preserve it and optionally add a secondary detailed description.
- **Image filtering controls** — Flags to skip decorative images (icons, avatars, logos) while keeping content images; needs careful design to avoid false positives.
- **Configurable front matter** — Flags to control which metadata fields are included.
- **Folder collision options** — `--on-conflict {fail,overwrite,suffix}` flag. Default changes to `suffix` (timestamp-based) in a future version.
- **Batch processing** — Accept multiple URLs or a file of URLs.
- **Pluggable content extraction** — Swap Jina for percollate, readability-cli, or other backends via a `--provider` flag.
- **CLI UI improvements** — `--verbose` and `--quiet` flags, progress bars, color output via `rich`.
- **MCP server / Claude Code skill** — Expose as a tool that AI agents can invoke directly.
- **Offline / self-hosted mode** — Use self-hosted Jina or local Readability.js pipeline with no external API calls.

## Code Quality (from PR #5 review)

- **Shared SSRF validation helper** — Extract `is_private_host()` from `cli.validate_url` and `images._is_private_url` into a common module to prevent drift between the two implementations.
- **Non-destructive log redaction** — `RedactionFilter` currently mutates `record.msg` in place; store redacted output in a custom attribute so handlers without the filter still see the original message.
- **Logging test isolation** — Add an autouse pytest fixture that calls `shutdown_logging()` after each test to prevent cross-test handler contamination from the module-level globals.

## Test Coverage (from PR #5 review)

- **CLI exit code integration test** — Test `main()` end-to-end with invalid URLs and assert the actual exit code (currently only unit-tested via `validate_url`).
- **`_safe_get` redirect hop counting test** — Test with actual 302 responses via `responses` library instead of mocking `Session.get` directly, to exercise the full redirect-counting loop.

## Open Questions

- **Alt text architecture (v2):** When existing alt text is present, should AI descriptions replace it, supplement it, or be added as a separate field? Needs more design work. Initial thinking: preserve original, add AI description as a secondary field if the original is substantive; replace if the original is empty/generic.
- **Image format handling (post-v1):** Should very large images be optionally compressed? Should WebP be converted to PNG/JPG for wider compatibility? TBD based on real-world usage.
- **HTML `<img>` support:** Should this be promoted from best-effort to fully supported in a future version? Depends on how often Jina emits `<img>` tags in practice.
