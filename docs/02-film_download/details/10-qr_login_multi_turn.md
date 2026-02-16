# DOCUMENT METADATA
title: QR Login Multi-Turn Flow - Summary
filename: 10-qr_login_multi_turn.md
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
> Summary of Task 10: Implement QR Login Multi-Turn Flow for Cloud115Tool.

---

## Implementation Summary

The multi-turn QR login flow was already implemented as part of Task 6 (Cloud115Tool). The login state machine works as follows:

**Turn N** - User initiates login:
1. Agent calls `cloud115(action="login")`
2. Tool generates QR code via `_generate_qr()`, stores `_login_uid` internally
3. Returns base64 QR image + instruction text
4. Agent sends QR image to user via Feishu

**Turn N+1** - User confirms scan:
1. User says "已扫码"
2. Agent calls `cloud115(action="check_session")`
3. Tool detects `_login_uid` is set, calls `_poll_login_status()`
4. Polls 115 API every 2 seconds for up to 120 seconds
5. On confirmation: saves cookies to session file, creates client, clears `_login_uid`
6. Returns `{"logged_in": true, "message": "登录成功"}`

This design works within nanobot's constraint that a tool cannot pause mid-execution to wait for user input. The state is split across two separate tool invocations.

## Files Changed

No additional files were modified for this task — the implementation was completed in Task 6.

Relevant code: `nanobot/agent/tools/cloud115.py` lines 87-138 (`_do_login`, `_do_check_session`, `_poll_login_status`).

## Test Results

Existing tests cover this flow:
```
tests/test_cloud115.py::test_cloud115_login_generates_qr PASSED
tests/test_cloud115.py::test_cloud115_check_session_with_pending_login PASSED
```

## Issues & Notes

- The `_login_uid` state is stored in-memory on the tool instance, not persisted to file. If the agent process restarts between Turn N and Turn N+1, the pending login state is lost. For production use, this could be persisted to the session file.
- The 120-second polling timeout in `_poll_login_status` is blocking within the tool's `execute()` call. For the "已扫码" pattern, this is acceptable since the user has already indicated they've scanned.
- QR code expiry is handled: if the 115 API returns status -1 or -2, the tool returns `{"status": "expired"}`.
