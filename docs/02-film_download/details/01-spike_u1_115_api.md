# DOCUMENT METADATA
title: Spike U1 — 115 API Library Validation Results
filename: 01-spike_u1_115_api.md
status: Draft
version: 1.0.0
owner: AI Assistant
last_updated: 2026-02-11
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-11 | Claude | Initial creation       |

## Purpose & Scope
> Summary of Spike U1: Validate that p115client can complete the full 115.com QR login → session save → magnet add cycle via HTTP API.

---

## Implementation Summary

### Library Used
- **p115client** (primary) — async-capable 115.com client via `async_=True` parameter
- py115 available as fallback but not tested

### Spike Script
- `tests/spike/spike_115_api.py`

### Key API Methods Discovered

| Method | Purpose | Notes |
|--------|---------|-------|
| `P115Client.login_qrcode_token(async_=True)` | Get QR code UID | Returns `{"data": {"uid": "..."}}` |
| `P115Client.login_qrcode_scan_status({"uid": uid}, async_=True)` | Poll scan status | 0=waiting, 1=scanned, 2=confirmed, -1=expired |
| `P115Client.login_qrcode_scan_result({"uid": uid, "app": "web"}, async_=True)` | Get login cookies | Call after status=2 |
| `P115Client(cookies_path, check_for_relogin=True)` | Reload session | Auto re-auth on 405 |
| `P115Client.offline_add_urls(payload, async_=True)` | Add magnet link | `payload={"urls": magnet, "wp_path_id": folder_id}` |
| `P115Client.offline_list(async_=True)` | List download tasks | Returns task array |
| `P115Client.user_info(async_=True)` | Validate session | Check `state` field |

### QR Code Lifecycle
- QR image URL format: `https://qrcodeapi.115.com/api/1.0/mac/1.0/qrcode?uid={uid}`
- Poll interval: 2 seconds
- Expiry time: ~120 seconds (configurable)
- Image format: PNG

### Credential Serialization
- Cookies stored as JSON at `~/.nanobot/cloud115_session.json`
- Key cookies: CID, SEID, UID
- `check_for_relogin=True` enables auto-recovery on 405

### Error Codes
| Code | Meaning |
|------|---------|
| 405  | Session expired (triggers re-login if `check_for_relogin=True`) |
| `state=false` | API call failed, check `errno` and `error` fields |

## Test Results

> **Status: PENDING** — Run `python tests/spike/spike_115_api.py` manually to validate.

## Issues & Notes
- QR login requires manual phone scanning — cannot be automated
- `check_for_relogin=True` is critical for production use (auto re-auth)
- All API methods support async via `async_=True` parameter
- Session file path is configurable via Cloud115Config
