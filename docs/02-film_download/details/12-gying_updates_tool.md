# DOCUMENT METADATA
title: GyingUpdatesTool - Summary
filename: 12-gying_updates_tool.md
status: Approved
version: 1.0.0
owner: AI Assistant
last_updated: 2026-02-15
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-15 | Claude | Initial creation       |

## Purpose & Scope
> Summary of Task 12: Implement GyingUpdatesTool for daily new release checks.

---

## Implementation Summary

Created `GyingUpdatesTool` class in `nanobot/agent/tools/gying.py` for checking gying.org for new movie releases and comparing against a local `seen_movies.json` deduplication file.

Key features:
1. **Listing scrape**: Navigates to gying.org homepage and extracts movie listings using `ul.content-list li` selectors.
2. **Deduplication**: Compares scraped URLs against `seen_movies.json` to identify new entries only.
3. **Result limiting**: `max_results` parameter caps the number of new movies returned (default: 10).
4. **State persistence**: After each check, updates `seen_movies.json` with newly discovered movies and a `last_check` timestamp.
5. **Shared browser**: Reuses `GyingScraperTool`'s Playwright browser instance to avoid launching multiple browsers.

Return format:
```json
{
  "new_movies": [...],
  "total_checked": 30,
  "previously_seen": 27,
  "new_count": 3
}
```

The tool was also registered in `AgentLoop._register_default_tools()` conditionally when `config.integrations.gying.enabled` is True. The `seen_file` path defaults to `{workspace}/film_download/seen_movies.json`.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nanobot/agent/tools/gying.py` | Modified | Added GyingUpdatesTool class (~120 lines) |
| `nanobot/agent/loop.py` | Modified | Register GyingUpdatesTool alongside GyingScraperTool |
| `tests/test_gying_updates.py` | Created | 6 test cases for updates tool |
| `tests/test_tool_registration.py` | Modified | Added test for GyingUpdatesTool registration |

## Test Results

```
tests/test_gying_updates.py::test_gying_updates_tool_interface PASSED
tests/test_gying_updates.py::test_gying_updates_returns_new_movies PASSED
tests/test_gying_updates.py::test_gying_updates_filters_seen PASSED
tests/test_gying_updates.py::test_gying_updates_saves_seen PASSED
tests/test_gying_updates.py::test_gying_updates_no_new_movies PASSED
tests/test_gying_updates.py::test_gying_updates_max_results PASSED
tests/test_tool_registration.py::test_gying_updates_tool_registered_when_enabled PASSED
```

All 7 related tests pass.

## Issues & Notes

- The `seen_movies.json` file grows unbounded. Cleanup of entries older than 90 days is planned for Task 16.
- Temp file encoding on Windows requires explicit `encoding="utf-8"` in tests to handle Chinese characters correctly.
