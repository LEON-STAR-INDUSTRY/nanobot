# DOCUMENT METADATA
title: GyingScraperTool - Summary
filename: 07-gying_scraper_tool.md
status: Approved
version: 1.1.0
owner: AI Assistant
last_updated: 2026-02-19
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-15 | Claude | Initial creation       |
| 1.1.0   | 2026-02-19 | Claude | Updated links action: tab-based quality filtering replaces text matching |

## Purpose & Scope
> Summary of Task 7: Implement GyingScraperTool for Playwright-based gying.org scraping.

---

## Implementation Summary

Created `GyingScraperTool`, a nanobot Tool that uses Playwright to scrape movie data from the gying.org SPA. The tool supports three actions:

1. **`search`**: Searches gying.org by keyword. Navigates to homepage, fills search input, presses Enter, and extracts up to 10 results (title, URL, rating).
2. **`detail`**: Gets full movie detail from a detail page URL. Extracts title, year, Douban/IMDB ratings, genres, synopsis, and poster URL.
3. **`links`**: Extracts magnet download links filtered by quality tab panels. Navigates the DOM tab→panel structure to extract links only from matching tabs (default: "中字4K" and "中字1080P"). Each link includes a `quality_tab` field indicating its source tab. Returns empty list if no matching tabs found.

Key design decisions:
- **Lazy browser launch**: Playwright browser is only started on first tool call via `_ensure_browser()`.
- **Persistent browser context**: Uses `launch_persistent_context` with `user_data_dir` for cookie retention across restarts.
- **Anti-detection**: Applies `playwright-stealth` if available, falls back to manual `navigator.webdriver` removal.
- **Validated CSS selectors**: All selectors were validated against real gying.org HTML dumps during Spike U2.

CSS Selector Map:

| Purpose | Selector |
|---------|----------|
| Search input | `input[type="search"]` |
| Search results | `.sr_lists .v5d` |
| Result title | `.text b a.d16` |
| Detail title | `.main-ui-meta h1 div` |
| Detail year | `.main-ui-meta h1 span.year` |
| Detail rating | `.ratings-section .freshness` |
| Download quality tabs | `.down-link .nav-tabs li` |
| Download rows | `table.bit_list tbody tr` |
| Magnet link | `a.torrent[href^="magnet:"]` |
| Homepage items | `ul.content-list li` |

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nanobot/agent/tools/gying.py` | Created | GyingScraperTool implementation (284 lines) |
| `tests/test_gying.py` | Created | 7 test cases with mocked Playwright calls |

## Test Results

```
tests/test_gying.py::test_gying_tool_interface PASSED
tests/test_gying.py::test_gying_search_returns_json PASSED
tests/test_gying.py::test_gying_search_requires_query PASSED
tests/test_gying.py::test_gying_detail_returns_movie_info PASSED
tests/test_gying.py::test_gying_detail_requires_url PASSED
tests/test_gying.py::test_gying_links_returns_magnets PASSED
tests/test_gying.py::test_gying_links_with_quality_filter PASSED
```

All 7 tests pass. No Playwright installation required for testing (internal methods are mocked).

## Issues & Notes

- gying.org is a full SPA — HTTP fetch returns empty HTML. Playwright is mandatory.
- The browser instance is shared across all actions within the same tool lifecycle. The `close()` method should be called when the tool is no longer needed.
- Quality filtering uses DOM tab→panel navigation: matches tab labels containing "中字4K"/"中字1080P", then extracts rows only from matched panels. This avoids confusion with bare "4K"/"1080P" tabs. See `18-quality_tab_filtering_and_update_modes.md` for details.
- Homepage listing selectors (for Scenario B) are validated but not yet used by this tool — they will be used by `GyingUpdatesTool` (Task 12).
