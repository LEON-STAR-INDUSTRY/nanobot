# DOCUMENT METADATA
title: Register Tools in AgentLoop - Summary
filename: 08-register_tools.md
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
> Summary of Task 8: Conditionally register Cloud115Tool and GyingScraperTool in AgentLoop based on configuration.

---

## Implementation Summary

Modified `AgentLoop.__init__` to accept an optional `config` parameter and updated `_register_default_tools()` to conditionally register integration tools when their respective config flags are enabled.

Changes made:
1. Added `config: "Config | None" = None` parameter to `AgentLoop.__init__`.
2. Added conditional registration block at the end of `_register_default_tools()`:
   - If `config.integrations.gying.enabled` is True: registers `GyingScraperTool` with `browser_data_dir` and `headless` from config.
   - If `config.integrations.cloud115.enabled` is True: registers `Cloud115Tool` with `session_path` and `default_save_path` from config.
3. Updated both call sites in `nanobot/cli/commands.py` (gateway and agent commands) to pass the `config` object to `AgentLoop`.

The tools use lazy imports (`from nanobot.agent.tools.gying import ...`) inside the conditional blocks to avoid import errors when Playwright or p115client are not installed.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nanobot/agent/loop.py` | Modified | Added `config` parameter, conditional tool registration |
| `nanobot/cli/commands.py` | Modified | Pass `config=config` to both AgentLoop instantiation sites |
| `tests/test_tool_registration.py` | Created | 8 test cases for conditional registration |

## Test Results

```
tests/test_tool_registration.py::test_gying_tool_registered_when_enabled PASSED
tests/test_tool_registration.py::test_gying_tool_not_registered_when_disabled PASSED
tests/test_tool_registration.py::test_cloud115_tool_registered_when_enabled PASSED
tests/test_tool_registration.py::test_cloud115_tool_not_registered_when_disabled PASSED
tests/test_tool_registration.py::test_both_tools_registered_when_both_enabled PASSED
tests/test_tool_registration.py::test_no_config_means_no_integration_tools PASSED
tests/test_tool_registration.py::test_cloud115_tool_uses_config_values PASSED
tests/test_tool_registration.py::test_gying_tool_uses_config_values PASSED
```

All 8 tests pass. Full suite (34 tests) passes with no regressions.

## Issues & Notes

- When no `config` is passed (backward compatibility), no integration tools are registered. This preserves existing behavior.
- The `config` parameter uses a forward reference string annotation (`"Config | None"`) to avoid circular imports, following the existing pattern for `ExecToolConfig` and `CronService`.
