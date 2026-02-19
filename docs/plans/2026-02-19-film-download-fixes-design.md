# DOCUMENT METADATA
title: Film Download - Quality Tab Filtering & Manual Update Trigger
filename: 2026-02-19-film-download-fixes-design.md
status: Approved
version: 1.0.0
owner: AI Assistant
last_updated: 2026-02-19
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-19 | Claude | Initial creation       |

## Purpose & Scope
> 修复影片下载流程中的两个问题：(1) 下载链接未按质量 tab 过滤，且 LLM 会伪造链接；(2) 最新影片检索只能通过 cron 触发，无法由用户主动唤起。

---

## 问题描述

### 问题 1：下载链接质量过滤失效

`_links()` 方法无差别抓取详情页全部 `download_rows`，没有按照 gying.org 页面的质量筛选 tab（"中字1080P"、"中字4K"）过滤。当前的 `quality` 参数只做事后文本匹配，不可靠。更严重的是，LLM 有时完全跳过工具调用，直接伪造下载链接返回给用户。

### 问题 2：最新影片检索不支持手动触发

`gying_check_updates` 工具已实现，但 SKILL.md 只将其描述为 cron 定时任务的触发目标。用户发送"帮我检索最新的电影"时，LLM 不知道应调用此工具。

## 设计方案

### Fix 1：Tool 层 — `_links()` 按 tab 过滤

**修改文件**: `nanobot/agent/tools/integrations/gying/tool.py`

**当前行为**: `_links()` 抓取页面上所有 `table.bit_list tbody tr`，不区分 tab。

**目标行为**:

1. 查询 `download_quality_tabs`（`.down-link .nav-tabs li`）获取所有 tab 标签文本
2. 找到 text 包含 "中字1080P" 或 "中字4K" 的 tab
3. 通过 tab 内 `<a>` 元素的 `href`（如 `#tab-3`）或 `data-bs-target` 属性定位对应的 `.tab-pane` 面板
4. 仅从匹配面板中的 `download_rows` 提取磁力链接
5. 每条链接标记所属 tab（`"quality_tab": "中字4K"`）
6. 如果两个 tab 都不存在 → 返回空列表

**`execute()` 中的 `quality` 参数改为 tab 选择器**:
- `quality="4K"` → 只取 "中字4K" tab
- `quality="1080P"` → 只取 "中字1080P" tab
- `quality=""` (默认) → 取 "中字4K" + "中字1080P" 两个 tab

**不使用点击**：headless 模式下不依赖 tab 点击事件。通过 DOM 结构（tab → panel 的 href/target 关联）直接定位目标面板抓取。

### Fix 2：Prompt 层 — SKILL.md 强化

**修改文件**: `nanobot/skills/film-download/SKILL.md`

#### 场景 A 第三步增加强制指令

```markdown
### 第三步：获取下载链接

用户回复分辨率偏好后：

1. **必须**调用 `gying_search`，action="links"，url=影片URL，quality=用户选择

> **重要：你必须调用 gying_search action="links" 获取下载链接。
> 严禁跳过工具调用或自行编造下载链接。
> 如果工具返回空结果，直接告知用户"未找到中字下载资源"。**
```

#### 场景 B 扩展手动触发

```markdown
## 场景 B：检查最新影片

### 触发条件（任一匹配即触发）：
- 定时任务消息（包含"检查 gying.org"或"检查新片"）
- 用户说"最新电影"、"最新影片"、"检索新片"、"有什么新片"、"帮我看看新片"等

> **重要：当用户要求查看最新影片时，你必须调用 gying_check_updates 工具。
> 严禁跳过工具调用或自行编造影片列表。**
```

处理流程不变：调用 `gying_check_updates` → 格式化新片列表 → 用户选择后衔接场景 A 第二步。

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `nanobot/agent/tools/integrations/gying/tool.py` | `_links()` 重写为 tab 面板过滤；`execute()` 中 quality 参数语义调整 |
| 修改 | `nanobot/skills/film-download/SKILL.md` | 场景 A 第三步加强制工具调用指令；场景 B 扩展手动触发条件 |
| 修改 | `tests/test_gying.py` | 更新 _links 相关测试 |
| 修改 | `tests/integration/test_film_workflow.py` | 更新 links 测试数据结构 |

## 验证方案

1. `_links()` 单元测试：mock 包含 tab + panel 结构的 DOM，验证只抓取目标 tab 的链接
2. SKILL.md 修改后运行 gateway，通过飞书测试：
   - 发送"帮我找 星际穿越" → 选择 → 要求 4K → 确认工具被调用且结果来自 "中字4K" tab
   - 发送"帮我检索最新的电影" → 确认 `gying_check_updates` 被调用
3. 全部 75 个现有测试通过
