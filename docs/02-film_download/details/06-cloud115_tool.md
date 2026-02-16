# DOCUMENT METADATA
title: Cloud115Tool - Summary
filename: 06-cloud115_tool.md
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
> Summary of Task 6: Implement Cloud115Tool for 115.com QR login and offline magnet download.

---

## Implementation Summary

Created `Cloud115Tool`, a nanobot Tool that wraps the `p115client` library for interacting with 115.com cloud storage. The tool supports four actions:

1. **`login`**: Generates a QR code for 115 mobile app scanning. Returns base64-encoded QR image and instructions. Stores pending login UID internally.
2. **`check_session`**: Checks login status. If a QR scan is pending, polls the 115 API for confirmation. If already logged in, validates the session. Falls back to loading from session file.
3. **`add_magnet`**: Adds a magnet link to 115's offline download queue. Auto-checks session validity first.
4. **`task_status`**: Queries the current offline download task list (up to 10 tasks).

Key design decisions:
- Multi-turn QR login: `login` generates QR and returns immediately; `check_session` on the next turn polls for confirmation.
- Session persistence via JSON file containing cookies dict.
- Lazy client creation: `p115client` is imported only when needed.
- All 115 API calls use `async_=True` for async operation.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nanobot/agent/tools/cloud115.py` | Created | Cloud115Tool implementation (262 lines) |
| `tests/test_cloud115.py` | Created | 7 test cases with mocked backends |

## Test Results

```
tests/test_cloud115.py::test_cloud115_tool_interface PASSED
tests/test_cloud115.py::test_cloud115_check_session_no_session PASSED
tests/test_cloud115.py::test_cloud115_add_magnet_not_logged_in PASSED
tests/test_cloud115.py::test_cloud115_login_generates_qr PASSED
tests/test_cloud115.py::test_cloud115_check_session_with_pending_login PASSED
tests/test_cloud115.py::test_cloud115_add_magnet_success PASSED
tests/test_cloud115.py::test_cloud115_task_status PASSED
```

All 7 tests pass. No external dependencies required for testing (all mocked).

## Issues & Notes

- The `_validate_client` method creates a new event loop internally (`asyncio.new_event_loop()`). This works via `asyncio.to_thread()` but could be improved if the p115client provides a sync validation method.
- Session file format: `{"cookies": {"UID": "...", "CID": "..."}}`.
- The tool does not yet handle automatic re-login on session expiry during `add_magnet` (planned for Task 15).
