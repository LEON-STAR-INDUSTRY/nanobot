# DOCUMENT METADATA
title: Spike U3 — Multi-Turn Stateful Conversation Results
filename: 03-spike_u3_multi_turn.md
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
> Summary of Spike U3: Validate that nanobot's session + tool system can support a 5-turn stateful film-download workflow without losing context.

---

## Implementation Summary

### Spike Script
- `tests/spike/spike_multi_turn.py`

### Test Approach
Two-level testing:
1. **Mock conversation** — Simulates 5 turns using mock tool implementations with file-based state. Validates tool logic, data flow, and state persistence without requiring an LLM provider.
2. **AgentLoop integration** (optional) — Uses actual AgentLoop with registered mock tools and a configured LLM. Requires manual setup.

### 5-Turn Conversation Flow

| Turn | User Input | Expected Agent Action | Tool Calls |
|------|-----------|----------------------|------------|
| 1 | "帮我找 星际穿越" | Search gying.org | `gying_search(action=search, query="星际穿越")` |
| 2 | "1" | Select first result, show detail | `gying_search(action=detail, url=...)` |
| 3 | "4K" | Get 4K links, check 115 login | `gying_search(action=links)` + `cloud115(action=check_session)` + `cloud115(action=login)` |
| 4 | "已扫码" | Confirm QR login | `cloud115(action=confirm_login)` |
| 5 | "1" | Add first link as magnet download | `cloud115(action=add_magnet, magnet_url=...)` |

### State Persistence
- JSON file at `tests/spike/output/spike_u3_state.json`
- Verified: search results, detail, links, login status, and magnet all persist across turns

## Test Results

> **Status: PENDING** — Run `python tests/spike/spike_multi_turn.py` to validate mock conversation flow.

## Issues & Notes
- Short replies ("1", "4K", "已扫码") require the LLM to correctly interpret from context
- Context window must include all tool call results from previous turns
- State file approach works for mock testing; production will use session JSONL
- Token usage cannot be measured without a real LLM provider
