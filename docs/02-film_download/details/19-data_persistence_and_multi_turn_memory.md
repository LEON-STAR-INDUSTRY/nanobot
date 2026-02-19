# DOCUMENT METADATA
title: 影片下载数据持久化与多轮记忆机制
filename: 19-data_persistence_and_multi_turn_memory.md
status: Approved
version: 1.0.0
owner: AI Assistant
last_updated: 2026-02-19
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-19 | Claude | Initial creation — 完整记录数据持久化机制和多轮交互解决方案 |

## Purpose & Scope
> 本文档详细说明影片下载功能的数据持久化架构，包括 session 会话存储、`seen_movies.json` 统一影片数据中心、以及多轮交互中序号选择的实现机制。面向后续维护和功能扩展参考。

---

## 1. 问题背景

### 1.1 原始问题

在多轮对话中，用户查询最新影片后回复序号（如 "3"），LLM 会编造影片 URL（如 `https://www.gying.org/movies/45776`），而非使用真实 URL（如 `/mv/823D`）。

### 1.2 根因分析

nanobot 的 session 机制只保存每轮对话的最终文本：

```
Session 保存（loop.py:321-322）:
  session.add_message("user", "查询最新的电影信息")
  session.add_message("assistant", "最新影片列表：\n1. 得闲谨制 (2025) 6.9 ...")

Session 读取（manager.py:52-53）:
  return [{"role": m["role"], "content": m["content"]} for m in recent]
```

**工具调用过程（含真实 URL）不被保存。** 下一轮对话中，LLM 只能看到格式化后的纯文本，无法获取结构化数据。

### 1.3 数据流示意（修复前）

```
Turn 1 内存 messages（完整）:
  system  → 系统提示
  user    → "查询最新的电影信息"
  assistant → (tool_calls: [{name: "gying_check_updates", ...}])
  tool    → {"movies": [{"url": "/mv/823D", ...}]}    ← 含真实URL
  assistant → "最新影片列表：\n1. ..."

Turn 1 保存到 session（精简）:
  user      → "查询最新的电影信息"
  assistant → "最新影片列表：\n1. ..."                   ← URL丢失

Turn 2 从 session 恢复:
  user      → "查询最新的电影信息"
  assistant → "最新影片列表：\n1. ..."                   ← 无URL，LLM被迫编造
```

## 2. 解决方案：统一影片数据中心

### 2.1 设计思路

**不修改 session 机制**（避免上下文膨胀），而是：

1. 将 `seen_movies.json` 从"cron 去重文件"升级为"影片数据中心"
2. 所有产生编号列表的操作（搜索、最新影片查询）自动将结果写入该文件
3. 新增 `action="select"` 动作，通过序号从缓存中查找真实 URL

### 2.2 数据结构

```json
{
  "movies": {
    "/mv/m7BA": {
      "title": "得闲谨制",
      "rating": "6.9",
      "tag": "剧情/战争",
      "first_seen": "2026-02-19",
      "notified": true
    },
    "/mv/823D": {
      "title": "惊变28年2：白骨圣殿",
      "rating": "7.2",
      "tag": "惊悚/恐怖",
      "first_seen": "2026-02-19",
      "notified": false
    }
  },
  "last_check": "2026-02-19T09:41:42+00:00",
  "last_query": {
    "timestamp": "2026-02-19T19:23:54+00:00",
    "urls": ["/mv/m7BA", "/mv/4LjJ", "/mv/823D", "/mv/GYoj", "..."]
  }
}
```

| 字段 | 用途 |
|------|------|
| `movies` | 全局影片注册表，URL 为 key，最多 100 条 |
| `movies[url].rating` | 影片评分（首页或搜索获取） |
| `movies[url].tag` | 类型标签 |
| `movies[url].first_seen` | 首次发现日期（YYYY-MM-DD） |
| `movies[url].notified` | 是否已通过 cron 推送通知 |
| `last_check` | 上次 cron 检查时间戳 |
| `last_query` | 最近一次展示给用户的编号列表 |
| `last_query.urls` | 有序 URL 列表，index 对应用户看到的编号（1-based） |

### 2.3 数据写入时机

| 场景 | 写入 movies | 写入 last_query | 设置 notified | 更新 last_check |
|------|-------------|-----------------|---------------|-----------------|
| `gying_check_updates` source="manual" | 全部追加/更新 | 写入 | 保持原值（新条目=false） | 不更新 |
| `gying_check_updates` source="cron" | 新发现条目追加 | 不写入 | 设为 true | 更新 |
| `gying_search` action="search" | 搜索结果追加/更新 | 写入 | 保持原值（新条目=false） | 不更新 |
| `gying_search` action="select" | 不写入（只读） | 不写入 | 不变 | 不变 |

### 2.4 清理策略

- **按时间清理**：`first_seen` 超过 90 天的条目自动删除
- **按数量上限**：超过 100 条时，按 `first_seen` 升序淘汰最旧的

## 3. 多轮交互流程（修复后）

### 3.1 数据流示意

```
Turn 1: "查询最新的电影信息"
  → gying_check_updates(source="manual")
  → 抓取12条 → 写入 movies + last_query
  → seen_movies.json:
      movies: {"/mv/m7BA": {...}, "/mv/823D": {...}, ...}
      last_query: {urls: ["/mv/m7BA", "/mv/4LjJ", "/mv/823D", ...]}
  → LLM 格式化文本回复（保存到 session）

Turn 2: "3"
  → gying_search(action="select", index=3)
  → 读取 last_query.urls[2] → "/mv/823D"
  → 读取 movies["/mv/823D"] → {title, rating, tag}
  → 返回 {"url": "/mv/823D", "title": "惊变28年2", ...}
  → LLM 拿到真实 URL
  → 继续调用 gying_search(action="detail", url="/mv/823D")
```

### 3.2 场景覆盖

| 场景 | 第一轮 | 第二轮（用户回复序号） |
|------|--------|----------------------|
| 场景 A：搜索影片 | `gying_search(action="search")` → 结果写入缓存 | `gying_search(action="select", index=N)` → 获取真实 URL |
| 场景 B：最新影片（手动） | `gying_check_updates(source="manual")` → 结果写入缓存 | `gying_search(action="select", index=N)` → 获取真实 URL |
| 场景 B：最新影片（cron） | `gying_check_updates(source="cron")` → 不写 last_query | 通常无多轮（通知场景） |

### 3.3 SKILL.md 核心规则

```markdown
⚠️ 核心规则：当用户回复数字序号时，你必须先调用 gying_search action="select"
获取该序号对应的真实影片URL。严禁根据上下文记忆猜测或编造URL。
```

## 4. Cron 去重机制

### 4.1 去重逻辑

cron 模式的去重判断：URL 是否已存在于 `movies` dict 中（不看 `notified` 字段）。

```python
seen_urls = set(seen_data.get("movies", {}).keys())
new_movies = [item for item in listing if item.get("url", "") not in seen_urls]
```

这意味着：
- **manual 写入的条目**（`notified=false`）也会被 cron 认为"已知"，不再重复通知
- 这是正确行为：用户手动查看过列表 → cron 不需要再推送

### 4.2 与 manual 模式的关系

| 操作 | 对 cron 去重的影响 |
|------|-------------------|
| manual 查询12条 → 12个 URL 写入 movies | cron 下次运行时这12个 URL 都是"已知"的 |
| cron 发现2条新片 → 2个 URL 写入 movies (notified=true) | 下次 cron 不再重复通知 |
| 新影片上线，URL 不在 movies 中 | cron 识别为新片并通知 |

**没有冲突**：两种模式操作同一个 `movies` dict，但写入时机不重叠（agent loop 串行处理消息）。

## 5. Session 存储机制（不变）

Session 机制本身未修改，保持以下行为：

### 5.1 保存内容

```python
# loop.py:321-322
session.add_message("user", msg.content)          # 用户原始文本
session.add_message("assistant", final_content)    # LLM 最终回复文本
```

### 5.2 不保存的内容

- 工具调用请求（function name, arguments）
- 工具返回结果（JSON 数据）
- 中间推理过程
- 系统提示

### 5.3 保存守卫

```python
# loop.py:315-319 — 防止无工具调用的短回复污染 session
if not used_tools and final_content and len(final_content) < 50:
    logger.warning("Skipping session save: short response without tool use")
```

### 5.4 文件格式

JSONL 文件，位于 `~/.nanobot/sessions/{channel}_{chat_id}.jsonl`：

```jsonl
{"_type": "metadata", "created_at": "...", "updated_at": "...", "metadata": {}}
{"role": "user", "content": "查询最新的电影信息", "timestamp": "..."}
{"role": "assistant", "content": "最新影片列表：\n1. ...", "timestamp": "..."}
```

## 6. 完整数据持久化架构

```
┌──────────────────────────────────────────────────────────┐
│                   用户消息进入                              │
└────────────────────┬─────────────────────────────────────┘
                     │
     ┌───────────────▼───────────────────┐
     │  SessionManager.get_or_create()   │
     │  加载历史: role + content          │
     └───────────────┬───────────────────┘
                     │
     ┌───────────────▼───────────────────┐
     │  ContextBuilder.build_messages()  │
     │  system + history + current       │
     └───────────────┬───────────────────┘
                     │
     ┌───────────────▼───────────────────┐
     │  LLM 调用 + 工具执行              │
     │                                    │
     │  工具写入 seen_movies.json:        │
     │  ├─ movies: {url → info}          │
     │  └─ last_query: {urls: [...]}     │
     │                                    │
     │  工具结果在 messages[] 中传递      │
     │  （不持久化到 session）             │
     └───────────────┬───────────────────┘
                     │
     ┌───────────────▼───────────────────┐
     │  Session 保存                      │
     │  只保存: user text + assistant text│
     └───────────────┬───────────────────┘
                     │
     ┌───────────────▼───────────────────┐
     │  下一轮对话                        │
     │                                    │
     │  session → 文本历史（无URL）        │
     │  seen_movies.json → 结构化数据     │
     │  action="select" → 从缓存取真实URL │
     └────────────────────────────────────┘
```

## 7. 相关文件

| 文件 | 职责 |
|------|------|
| `nanobot/agent/tools/integrations/gying/tool.py` | GyingScraperTool（search/detail/links/select）+ GyingUpdatesTool（manual/cron） |
| `nanobot/skills/film-download/SKILL.md` | LLM 行为指令，包含序号选择规则 |
| `nanobot/session/manager.py` | Session JSONL 读写（只存 role+content） |
| `nanobot/agent/loop.py` | Agent 主循环，session 保存逻辑 + tool_choice 重试 |
| `nanobot/agent/context.py` | 上下文构建（system prompt + history） |
| `{workspace}/film_download/seen_movies.json` | 统一影片数据中心 |

## 8. 测试覆盖

| 测试文件 | 覆盖内容 |
|----------|----------|
| `tests/test_gying.py` | select 序号解析、缓存写入、无效序号、无缓存场景 |
| `tests/test_gying_updates.py` | manual 写入全局注册表+last_query、preserves existing、100条上限 |
| `tests/integration/test_film_workflow.py` | 端到端场景 A 工作流 |
