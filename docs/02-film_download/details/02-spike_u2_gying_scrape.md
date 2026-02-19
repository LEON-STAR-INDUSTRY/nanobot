# DOCUMENT METADATA
title: Spike U2 — gying.org Playwright Scraping Results
filename: 02-spike_u2_gying_scrape.md
status: Approved
version: 1.1.0
owner: AI Assistant
last_updated: 2026-02-15
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-11 | Claude | Initial creation       |
| 1.1.0   | 2026-02-15 | Claude | Updated with actual test results, confirmed selectors, site structure analysis |

## Purpose & Scope
> Summary of Spike U2: Validate that Playwright can render the gying.org SPA, handle authentication, and extract movie data.

---

## Implementation Summary

### Spike Script
- `tests/spike/spike_gying_scrape.py`

### Browser Configuration
- Chromium with persistent `user_data_dir` for cookie retention
- `playwright-stealth` for anti-detection（可选，当前测试中已使用）
- Headed mode（首次需要手动登录）
- Locale: `zh-CN`, Viewport: 1280x800

### Login Mechanism
- gying.org 使用 cookie 认证
- 首次运行需在弹出的浏览器窗口中手动登录
- 登录后 cookies 通过 `user_data_dir` 持久化，后续运行自动复用
- 未发现 Cloudflare 挑战（当前）

### Site Structure（已验证）

gying.org 是一个 SPA，服务端返回空壳 HTML + JS，所有内容通过 JavaScript 渲染。WebFetch 无法获取内容，必须使用 Playwright。

**URL 模式:**
- 首页: `https://www.gying.org/`
- 电影详情: `/mv/{id}`（如 `/mv/ZKpM`）
- 剧集详情: `/tv/{id}`（如 `/tv/lDVn`）
- 种子详情: `/bt/{id}`
- 搜索: 通过 `input[type="search"]` + Enter 触发

## CSS Selectors（全部已验证通过）

### 搜索结果页

| 选择器 | 用途 | 说明 |
|--------|------|------|
| `input[type="search"]` | 搜索输入框 | 顶栏搜索框 |
| `.sr_lists .v5d` | 每条搜索结果 | 包含缩略图+文字信息 |
| `.text b a.d16` | 结果标题链接 | 在 `.v5d` 内部，href 如 `/mv/ZKpM` |
| `.text p` | 信息行（多个） | 类型、又名、评分、导演、主演各一个 `<p>`，评分行以 `评分：` 开头 |

### 详情页

| 选择器 | 用途 | 说明 |
|--------|------|------|
| `.main-ui-meta h1 div` | 电影标题 | 纯文本 |
| `.main-ui-meta h1 span.year` | 年份 | 格式 `(2019)` |
| `.ratings-section .freshness` | 评分 | 多个：第1个=豆瓣，第2个=IMDb，可能有第3个=烂番茄 |
| `.main-ui-meta a[href*="genre="]` | 类型标签 | 如 `剧情`、`科幻`，多个 `<a>` |
| `.main-ui-meta a[href*="/s/2---1/"]` | 演员链接 | 导演/编剧/主演共用类似结构 |
| `.movie-introduce .zkjj_a` | 简介（折叠版） | 末尾有 `[展开全部]` 按钮 |
| `.main-meta .img img` | 海报图片 | `src` 为 webp 格式 |

### 下载区（详情页下方）

| 选择器 | 用途 | 说明 |
|--------|------|------|
| `div#down` | 磁力下载区容器 | 包含质量筛选tabs和资源表格 |
| `.down-link .nav-tabs li` | 质量筛选tab | 如 `全部 11`、`1080P 2`、`中字1080P 3`、`4K 1`、`中字4K 5` |
| `table.bit_list tbody tr` | 资源行 | 每行一个磁力资源 |
| `a.torrent[href^="magnet:"]` | 磁力链接 | 在 `<tr>` 内部，`href` 为完整 magnet URI，`title` 和文本内容为文件名 |

**资源行结构:** `<tr>` 内有5个 `<td>`:
1. 文件名（含 `a.torrent` 磁力链接 + 详情链接）
2. 下载操作（磁力 · 种子 · 离线）
3. 文件大小
4. 做种数
5. 发布时间

**质量/字幕判断:** 通过文件名文本匹配：
- 4K: 包含 `4K` 或 `2160p`
- 1080P: 包含 `1080p`
- 中字: 包含 `中字` 或 `中文字幕`

**注意:** 质量筛选 tab 已由网站提供（`中字1080P`、`中字4K` 等），点击 tab 可过滤表格内容，也可直接遍历全部行后在代码中筛选。

### 首页列表

| 选择器 | 用途 | 说明 |
|--------|------|------|
| `ul.content-list li` | 影片卡片 | 电影和剧集共用此结构，混排在首页 |
| `.li-bottom h3 a` | 标题+链接 | href 区分类型：`/mv/` 为电影，`/tv/` 为剧集 |
| `.li-bottom h3 span` | 评分 | 无评分时显示 `--` |
| `.li-bottom div.tag` | 类型标签 | 格式：`2025 / 大陆 / 剧情 / 喜剧` |
| `a[href^="/mv/"]` | 电影链接 | 用于区分电影 vs 剧集 |

**首页电影 vs 剧集区分:**
- 首页有两个并列的 `div.wrap` 块，分别包含 `<h2>最近更新的电影</h2>` 和 `<h2>最近更新的剧集</h2>`
- 两者内部结构完全相同（`ul.content-list > li`）
- 区分方式：检查卡片内链接的 `href` 前缀，`/mv/` = 电影，`/tv/` = 剧集

## Test Results

| 测试项 | 结果 | 备注 |
|--------|------|------|
| Browser launch + stealth | ✅ PASS | Chromium 正常启动 |
| Page render | ✅ PASS | SPA 渲染成功 |
| Login | ✅ PASS | Cookie 持久化，自动复用 session |
| Search | ✅ PASS | 搜索"星际穿越"返回 5 条结果 |
| Detail | ✅ PASS | 提取到 title, year, douban_rating, imdb_rating, genres, synopsis, poster_src |
| Links | ✅ PASS | 111 条磁力链接，其中 5 条中字4K，2 条中字1080P |
| Listing | ✅ PASS | 首页 24 项（12 电影 + 12 剧集） |

## Files
- Script: `tests/spike/spike_gying_scrape.py`
- Results: `tests/spike/output/spike_u2_results.json`
- Selectors: `tests/spike/output/selectors.json`
- Screenshots: `tests/spike/output/screenshots/`
- Browser data: `tests/spike/output/gying_browser_data/` (gitignored)
- Storage state: `tests/spike/output/gying_storage_state.json` (gitignored)
