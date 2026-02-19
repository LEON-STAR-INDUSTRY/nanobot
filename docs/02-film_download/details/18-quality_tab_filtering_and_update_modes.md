# DOCUMENT METADATA
title: Quality Tab Filtering & Update Modes Refactor
filename: 18-quality_tab_filtering_and_update_modes.md
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
> 本次迭代包含两组改动：(1) GyingScraperTool 的 `_links()` 方法从全量抓取改为按质量标签页（tab panel）过滤；(2) GyingUpdatesTool 增加 `source` 参数区分用户主动查询与定时任务，并在 SKILL.md 中增加防伪造和排序约束。

---

## 一、下载链接质量标签过滤

### 背景

原 `_links()` 方法抓取页面上所有 `table.bit_list tbody tr` 行，通过文件名文本匹配过滤质量。但 gying.org 的下载区域按标签页（tab）组织，除了 "中字4K" 和 "中字1080P" 外，还存在不带 "中字" 前缀的 "4K"、"1080P" 等标签页。文本匹配无法区分这些标签页来源。

### 改动

**文件：** `nanobot/agent/tools/integrations/gying/tool.py`

1. **新增类常量** `QUALITY_TABS = ["中字4K", "中字1080P"]`，定义默认目标标签页。

2. **重写 `_links()` 方法签名：**
   ```python
   async def _links(self, url: str, quality_tabs: list[str] | None = None) -> list[dict]
   ```
   - 通过 CSS 选择器 `download_quality_tabs` 获取所有 `<li>` 标签元素
   - 遍历匹配目标标签（`if target in tab_text`），提取对应 panel 的 `id`
   - 仅从匹配的 panel 内部提取下载行
   - 每条链接增加 `quality_tab` 字段标识来源标签页

3. **重写 `execute()` links 分支：**
   - `quality="4K"` → `quality_tabs=["中字4K"]`
   - `quality="1080P"` → `quality_tabs=["中字1080P"]`
   - 空值 → `quality_tabs=None`（默认两个标签页都取）
   - 移除旧的 `filtered` / `filter` 返回字段，统一返回 `{"links": [...]}`

4. **更新 `quality` 参数描述**，明确为标签页选择器。

### 匹配安全性

匹配逻辑 `if target in tab_text` 中 `target` 为 `"中字4K"` / `"中字1080P"`（含中文前缀），不会误匹配裸 `"4K"` 或 `"1080P"` 标签页：

| tab_text | target="中字4K" | 结果 |
|----------|----------------|------|
| "4K"     | "中字4K" in "4K" | False (不匹配) |
| "中字4K" | "中字4K" in "中字4K" | True (匹配) |

---

## 二、GyingUpdatesTool 手动/定时模式

### 背景

原 `execute()` 方法无论触发来源，总是过滤已见影片并更新 `seen_movies.json`。实际需求：
- 用户主动查询"最新电影"：应返回首页全部 12 条影片
- 定时任务触发：只返回新增未通知的影片

另外，原 `category` 参数（`latest`/`trending`/`4k`/`all`）声明了但从未使用。

### 改动

**文件：** `nanobot/agent/tools/integrations/gying/tool.py`

1. **删除 `category` 参数**，新增 `source` 参数：
   ```python
   "source": {
       "type": "string",
       "enum": ["manual", "cron"],
       "description": "Trigger source: 'manual' returns all listings, 'cron' returns only unseen."
   }
   ```

2. **`execute()` 按 source 分支：**
   - `source="manual"`：返回全部列表，不过滤 seen，不更新 seen_movies.json
     - 返回字段：`{"movies": [...], "total": N, "count": N}`
   - `source="cron"`（默认）：过滤已见，更新 seen_movies.json
     - 返回字段：`{"new_movies": [...], "total_checked": N, "previously_seen": N, "new_count": N}`

3. **`max_results` 默认值** 从 10 改为 12，匹配首页显示条数。

---

## 三、SKILL.md 增强

**文件：** `nanobot/skills/film-download/SKILL.md`

### 防伪造规则

在场景 A 第三步和场景 B 中增加严格规则：

> ⚠️ 严格规则：你必须调用工具获取真实数据。严禁跳过工具调用或自行编造下载链接/影片列表。

### 场景 B 手动/定时区分

- **用户主动查询**（"最新电影"、"有什么新片"等）→ `source="manual"`，返回全部列表
- **定时任务触发**（"检查 gying.org"）→ `source="cron"`，只返回新增

### 排序约束

> ⚠️ 展示规则：必须严格按照工具返回的原始顺序展示影片列表，严禁按评分、标题或其他字段重新排序。

---

## 四、测试覆盖

| 测试文件 | 新增/修改 | 说明 |
|----------|----------|------|
| `tests/test_gying.py` | 修改 2 + 新增 1 | 更新 links 测试适配 quality_tab 字段，新增空标签页测试 |
| `tests/test_gying_updates.py` | 修改 6 + 新增 1 | `category` → `source="cron"`，新增 manual 模式测试 |
| `tests/integration/test_film_workflow.py` | 修改 3 | MOCK_LINKS 增加 quality_tab，更新 filtered 断言 |

**测试结果：** 77 passed, 0 failed

---

## 五、提交记录

| Commit | 说明 |
|--------|------|
| `ec3ba6c` | refactor: rewrite _links() to filter by quality tab panels |
| `18bc26d` | test: update gying link tests for tab-based quality filtering |
| `988c046` | test: update integration tests for tab-based link filtering |
| `bfaaac0` | feat: enforce tool calls in film skill, add manual update trigger |
| `e58d8e5` | feat: add source param to GyingUpdatesTool (manual/cron modes) |
