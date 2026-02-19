# DOCUMENT METADATA
title: Polish & Hardening - Summary
filename: 14-16-polish_hardening.md
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
> Summary of Tasks 14, 15, 16: Error handling & Chinese UX, session auto-recovery, and seen movies cleanup.

---

## Task 14: Error Handling & Chinese UX

All error messages across both tools are in Chinese. Error coverage includes:

| Scenario | Error Message |
|----------|--------------|
| gying.org scrape timeout | "抓取失败: TimeoutError: ..." |
| gying.org element not found | "抓取失败: RuntimeError: ..." |
| Missing search query | "缺少query参数，请提供搜索关键词" |
| Missing detail/links URL | "缺少url参数，请提供影片详情页URL" |
| Unknown action | "未知操作: {action}" |
| 115 not logged in | "未登录115，请先扫码登录。" |
| Missing magnet URL | "缺少magnet_url参数" |
| 115 API failure | "添加失败: {errcode} - {error_msg}" |
| 115 session expired | "115 登录已过期，请发送 '登录115' 重新扫码登录。" |
| Updates check failure | "检查更新失败: {error_type}: {error}" |

**13 error handling tests** created in `tests/test_error_messages.py`.

## Task 15: Session Auto-Recovery for 115

Enhanced `Cloud115Tool._do_add_magnet()` to detect session expiry from API error codes. Known expiry error codes: 911, 40101, 40100, 990001.

When an expired session is detected:
1. The `_client` is set to `None` (clearing the stale session)
2. Returns a message prompting re-login: "115 登录已过期，请发送 '登录115' 重新扫码登录。"
3. The `logged_in: false` flag is included to help the agent trigger the login flow

Pre-existing auto-check: both `_do_add_magnet` and `_do_task_status` already call `_do_check_session()` when `_client` is None, attempting to reload from the session file.

## Task 16: Seen Movies Cleanup

Added `_cleanup_seen()` method to `GyingUpdatesTool` that removes entries older than 90 days from `seen_movies.json`.

- Called automatically after each `check_updates` execution
- Uses `first_seen` date field to calculate age
- Default max age: 90 days
- Operates in-place on the data dict before saving

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nanobot/agent/tools/cloud115.py` | Modified | Session expiry detection in _do_add_magnet |
| `nanobot/agent/tools/gying.py` | Modified | Added _cleanup_seen method to GyingUpdatesTool |
| `tests/test_error_messages.py` | Created | 13 error handling tests |
| `tests/test_gying_updates.py` | Modified | Added cleanup test |

## Test Results

```
tests/test_error_messages.py: 13 passed
tests/test_gying_updates.py: 7 passed (including cleanup test)
```

All tests pass.
