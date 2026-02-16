# DOCUMENT METADATA
title: Spike U1 — 115 API Library Validation Results
filename: 01-spike_u1_115_api.md
status: Approved
version: 1.1.0
owner: AI Assistant
last_updated: 2026-02-15
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-11 | Claude | Initial creation       |
| 1.1.0   | 2026-02-15 | Claude | Updated with actual test results, corrected API usage patterns |

## Purpose & Scope
> Summary of Spike U1: Validate that p115client can complete the full 115.com QR login → session save → magnet add cycle via HTTP API.

---

## Implementation Summary

### Library
- **p115client** — async 115.com client
- 安装方式: `pip install -U git+https://github.com/ChenyangGao/p115client@main`
- py115 作为备选但未测试

### Spike Script
- `tests/spike/spike_115_api.py`

### Key API Patterns（已验证）

| 操作 | 代码 | 说明 |
|------|------|------|
| QR 登录 | `await P115Client.login_with_qrcode(app="web", console_qrcode=True, async_=True)` | 类方法，自动处理 QR 生成、展示、轮询；返回 login_result dict |
| 从登录结果创建客户端 | `P115Client(login_result)` | 传入 login_with_qrcode 的返回值 |
| 从已保存 cookie 创建客户端 | `P115Client(cookies_dict, check_for_relogin=True)` | cookies_dict 是 `{"UID": "xxx", "CID": "yyy", ...}` 形式的 dict |
| 验证 session | `await client.user_info(async_=True)` | 检查返回值 `state` 字段 |
| 添加磁力下载 | `await client.offline_add_urls(magnet_str, async_=True)` | 第一个参数直接传 magnet 字符串 |
| 查询下载列表 | `await client.offline_list(async_=True)` | 返回 `{"tasks": [...]}` |

### Credential Serialization（已验证）
- Session 文件格式: JSON
- 存储内容: `{"cookies": {"UID": "...", "CID": "...", ...}, "login_result": {...}}`
- Cookie 来源: `login_result["data"]["cookie"]`
- 重要: 传给 `P115Client()` 的是 cookies dict，**不是**文件路径
- `check_for_relogin=True` 在 session 过期时自动触发重新登录

### 注意事项
- `login_with_qrcode` 是**类方法**，不是实例方法
- `offline_add_urls` 第一个参数直接传 magnet 字符串，不需要包装成 `{"urls": ..., "wp_path_id": ...}` 的 dict
- 所有异步方法通过 `async_=True` 参数启用

## Test Results

| 测试项 | 结果 | 备注 |
|--------|------|------|
| QR 登录 | ✅ PASS | 首次运行通过 QR 扫码登录成功，后续运行使用 saved session |
| Session 保存/重载 | ✅ PASS | 从 JSON 文件重载 cookies，用户信息验证成功 |
| 添加磁力任务 | ✅ PASS | `offline_add_urls` 成功，`state=true` |
| 任务列表查询 | ✅ PASS | `offline_list` 正常返回任务列表 |

## Files
- Script: `tests/spike/spike_115_api.py`
- Results: `tests/spike/output/spike_u1_results.json`
- Session: `tests/spike/output/115_session.json` (gitignored)
