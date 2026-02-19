# Film Download Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix download link quality filtering to use gying.org's tab panels, and enhance SKILL.md to prevent LLM fabrication and support manual update triggers.

**Architecture:** Two independent changes: (1) Rewrite `_links()` to navigate the DOM tab→panel structure instead of scraping all rows, with `execute()` quality parameter becoming a tab selector. (2) Enhance SKILL.md with forced tool-call instructions and expanded Scenario B trigger conditions.

**Tech Stack:** Playwright (async), pytest + pytest-asyncio, markdown skill files.

---

### Task 1: Rewrite `_links()` to filter by quality tab panels

**Files:**
- Modify: `nanobot/agent/tools/integrations/gying/tool.py:84-134` (execute links branch + `_links()` method)

**Step 1: Rewrite `_links()` to use tab→panel DOM navigation**

Replace lines 290-320 of `nanobot/agent/tools/integrations/gying/tool.py` with:

```python
    # Target tab labels — only these tabs are relevant
    QUALITY_TABS = ["中字4K", "中字1080P"]

    async def _links(self, url: str, quality_tabs: list[str] | None = None) -> list[dict]:
        """Get magnet download links filtered by quality tab panels.

        Args:
            url: Movie detail page URL.
            quality_tabs: Tab labels to extract from (e.g. ["中字4K"]).
                          Defaults to QUALITY_TABS.

        Returns:
            List of link dicts, each with quality_tab field indicating source tab.
            Empty list if no matching tabs found on the page.
        """
        await self._ensure_browser()
        await self._ensure_logged_in()
        page = self._page

        # Navigate if not already on the right page
        current = page.url
        full_url = url if url.startswith("http") else BASE_URL + url
        if full_url not in current:
            await page.goto(full_url, wait_until="networkidle", timeout=30000)

        target_tabs = quality_tabs or self.QUALITY_TABS

        # Step 1: Find all tab elements and match target labels
        tab_els = await page.query_selector_all(SELECTORS["download_quality_tabs"])
        matched_panels = []  # [(panel_selector, tab_label)]
        for tab_el in tab_els:
            tab_text = (await tab_el.inner_text()).strip()
            for target in target_tabs:
                if target in tab_text:
                    # Find the <a> inside the tab <li> to get panel reference
                    a_el = await tab_el.query_selector("a")
                    if not a_el:
                        continue
                    panel_id = (
                        await a_el.get_attribute("href")
                        or await a_el.get_attribute("data-bs-target")
                        or await a_el.get_attribute("data-target")
                        or ""
                    )
                    if panel_id.startswith("#"):
                        matched_panels.append((panel_id, target))
                    break

        if not matched_panels:
            logger.info(f"No matching quality tabs found on {url} (wanted: {target_tabs})")
            return []

        # Step 2: Extract links from each matched panel
        links = []
        for panel_selector, tab_label in matched_panels:
            rows = await page.query_selector_all(
                f"{panel_selector} {SELECTORS['download_rows']}"
            )
            for row in rows:
                magnet_el = await row.query_selector(SELECTORS["magnet_link"])
                if not magnet_el:
                    continue
                name = (await magnet_el.inner_text()).strip()
                magnet = await magnet_el.get_attribute("href") or ""
                tds = await row.query_selector_all("td")
                size = (await tds[2].inner_text()).strip() if len(tds) >= 3 else ""
                seeds = (await tds[3].inner_text()).strip() if len(tds) >= 4 else ""
                links.append({
                    "name": name,
                    "magnet": magnet,
                    "size": size,
                    "seeds": seeds,
                    "quality_tab": tab_label,
                })

        return links
```

**Step 2: Update `execute()` links branch**

Replace lines 111-127 of `execute()` (the `elif action == "links":` branch) with:

```python
            elif action == "links":
                url = kwargs.get("url", "")
                if not url:
                    return json.dumps(
                        {"error": "缺少url参数，请提供影片详情页URL"}, ensure_ascii=False
                    )
                quality = kwargs.get("quality", "")
                # Map quality param to target tabs
                if quality.upper() == "4K":
                    quality_tabs = ["中字4K"]
                elif quality.upper() == "1080P":
                    quality_tabs = ["中字1080P"]
                else:
                    quality_tabs = None  # Default: both 中字4K + 中字1080P
                links = await self._links(url, quality_tabs=quality_tabs)
                return json.dumps({"links": links}, ensure_ascii=False)
```

**Step 3: Update `quality` parameter description**

Replace line 84-87 (the quality property in `parameters`) with:

```python
                "quality": {
                    "type": "string",
                    "description": "Quality tab filter: '4K' (中字4K tab), '1080P' (中字1080P tab), or empty for both.",
                },
```

**Step 4: Run tests**

Run: `pytest tests/ -v`

Expected: Some tests will fail because the mock data shape changed (links no longer have `filtered` key; links now have `quality_tab` field).

**Step 5: Commit**

```bash
git add nanobot/agent/tools/integrations/gying/tool.py
git commit -m "refactor: rewrite _links() to filter by quality tab panels

Instead of scraping all download rows and text-matching filenames,
navigate the DOM tab→panel structure to extract links only from
'中字4K' and '中字1080P' tabs. Returns empty list if no matching
tabs exist on the page."
```

---

### Task 2: Update unit tests for new `_links()` behavior

**Files:**
- Modify: `tests/test_gying.py:73-109`

**Step 1: Update `test_gying_links_returns_magnets`**

The mock return value now needs the `quality_tab` field, and `execute()` no longer returns `filtered` key — it returns just `links`.

Replace `test_gying_links_returns_magnets` (lines 73-90):

```python
@pytest.mark.asyncio
async def test_gying_links_returns_magnets():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    with patch.object(tool, "_links", new_callable=AsyncMock) as mock_links:
        mock_links.return_value = [
            {
                "name": "星际穿越.4K.中字.mkv",
                "magnet": "magnet:?xt=urn:btih:abc123",
                "size": "14.6GB",
                "seeds": "50",
                "quality_tab": "中字4K",
            },
        ]
        result = await tool.execute(action="links", url="/mv/ZKpM")
        data = json.loads(result)
        assert "links" in data
        assert len(data["links"]) == 1
        assert data["links"][0]["magnet"].startswith("magnet:")
        assert data["links"][0]["quality_tab"] == "中字4K"
```

**Step 2: Update `test_gying_links_with_quality_filter`**

Replace `test_gying_links_with_quality_filter` (lines 93-109):

```python
@pytest.mark.asyncio
async def test_gying_links_with_quality_filter():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    mock_4k_links = [
        {"name": "movie.4K.中字.mkv", "magnet": "magnet:?xt=urn:btih:aaa", "size": "14GB", "seeds": "30", "quality_tab": "中字4K"},
    ]
    with patch.object(tool, "_links", new_callable=AsyncMock) as mock_links:
        mock_links.return_value = mock_4k_links
        result = await tool.execute(action="links", url="/mv/ZKpM", quality="4K")
        data = json.loads(result)
        assert "links" in data
        assert len(data["links"]) == 1
        # Verify quality_tabs argument was passed correctly
        mock_links.assert_called_once_with("/mv/ZKpM", quality_tabs=["中字4K"])
```

**Step 3: Add test for empty tabs (no matching quality)**

Add new test after the quality filter test:

```python
@pytest.mark.asyncio
async def test_gying_links_no_matching_tabs():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    with patch.object(tool, "_links", new_callable=AsyncMock) as mock_links:
        mock_links.return_value = []  # No matching tabs
        result = await tool.execute(action="links", url="/mv/ZKpM", quality="4K")
        data = json.loads(result)
        assert data["links"] == []
```

**Step 4: Run tests**

Run: `pytest tests/test_gying.py -v`

Expected: All gying tests pass.

**Step 5: Commit**

```bash
git add tests/test_gying.py
git commit -m "test: update gying link tests for tab-based quality filtering"
```

---

### Task 3: Update integration tests for new link data shape

**Files:**
- Modify: `tests/integration/test_film_workflow.py:38-51, 93-109, 208-213`

**Step 1: Update `MOCK_LINKS` data**

Replace lines 38-51:

```python
MOCK_LINKS = [
    {
        "name": "星际穿越.4K.中英字幕.mkv",
        "magnet": "magnet:?xt=urn:btih:abc123def456",
        "size": "45.2GB",
        "seeds": "128",
        "quality_tab": "中字4K",
    },
    {
        "name": "星际穿越.1080p.中字.mp4",
        "magnet": "magnet:?xt=urn:btih:789xyz",
        "size": "4.5GB",
        "seeds": "256",
        "quality_tab": "中字1080P",
    },
]
```

**Step 2: Update `test_links_returns_filtered_magnets`**

Replace lines 93-109:

```python
@pytest.mark.asyncio
async def test_links_returns_filtered_magnets():
    """Turn 3: Get download links with quality filter."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    url = MOCK_SEARCH_RESULTS[0]["url"]
    # When quality="4K", only 中字4K tab links are returned
    mock_4k_links = [lk for lk in MOCK_LINKS if lk["quality_tab"] == "中字4K"]
    with patch.object(tool, "_links", new_callable=AsyncMock) as mock:
        mock.return_value = mock_4k_links
        result = await tool.execute(action="links", url=url, quality="4K")
        data = json.loads(result)

        assert "links" in data
        assert len(data["links"]) == 1
        assert data["links"][0]["name"] == "星际穿越.4K.中英字幕.mkv"
        assert data["links"][0]["quality_tab"] == "中字4K"
        mock.assert_called_once_with(url, quality_tabs=["中字4K"])
```

**Step 3: Update workflow test Turn 3**

Replace lines 208-213 in `test_full_scenario_a_workflow`:

```python
    # Turn 3: Links
    mock_4k_links = [lk for lk in MOCK_LINKS if lk["quality_tab"] == "中字4K"]
    with patch.object(gying, "_links", new_callable=AsyncMock) as mock:
        mock.return_value = mock_4k_links
        r3 = json.loads(await gying.execute(action="links", url=selected_url, quality="4K"))
    assert len(r3["links"]) == 1
    selected_magnet = r3["links"][0]["magnet"]
```

**Step 4: Run all tests**

Run: `pytest tests/ -v`

Expected: All 75 tests pass.

**Step 5: Commit**

```bash
git add tests/integration/test_film_workflow.py
git commit -m "test: update integration tests for tab-based link filtering"
```

---

### Task 4: Enhance SKILL.md with forced tool-call instructions and manual trigger

**Files:**
- Modify: `nanobot/skills/film-download/SKILL.md`

**Step 1: Update Scenario A Step 3 with enforcement**

Replace lines 44-57 (current "第三步" section):

```markdown
### 第三步：获取下载链接

用户回复分辨率偏好后：

1. **必须**调用 `gying_search`，action="links"，url=影片URL，quality=用户选择的分辨率

> **⚠️ 严格规则：你必须调用 gying_search action="links" 获取真实的下载链接。严禁跳过工具调用或自行编造下载链接、文件名、磁力链接。如果工具返回空列表，直接告知用户"未找到中字下载资源"。**

2. 展示返回的链接列表：

```
找到以下中字4K资源：
1. Movie.2024.2160p.BluRay.中英字幕 (45.2 GB)
2. Movie.2024.2160p.HDR.WEB-DL.中字 (18.7 GB)

请回复序号选择下载
```

3. 如果返回空列表：回复"未找到该分辨率的中字下载资源，请尝试其他分辨率。"
```

**Step 2: Rewrite Scenario B to support both cron and manual triggers**

Replace lines 74-91 (current "场景 B" section):

```markdown
## 场景 B：检查最新影片

### 触发条件（任一匹配即触发）：

- 定时任务消息（包含"检查 gying.org"或"检查新片"）
- 用户说"最新电影"、"最新影片"、"检索新片"、"有什么新片"、"帮我看看新片"、"最近有什么好看的"等

> **⚠️ 严格规则：当用户要求查看最新影片时，你必须调用 gying_check_updates 工具获取真实数据。严禁跳过工具调用或自行编造影片列表。**

### 处理流程：

1. 调用 `gying_check_updates`，category="latest"
2. 如果没有新影片：回复"暂无新影片更新"
3. 如果有新影片，格式化为编号列表：

```
发现 3 部新影片：
1. 沙丘3 Dune: Part Three (2026) 8.7
2. 黑暗骑士归来 (2026) 9.1
3. 流浪地球3 (2026) 8.3

回复序号查看详情并下载
```

4. 用户回复序号后，从场景 A 第二步继续
```

**Step 3: Update error handling section**

Replace line 107 ("没有匹配分辨率" entry):

```markdown
- 没有匹配分辨率的中字资源：回复"未找到该分辨率的中字下载资源，请尝试其他分辨率（4K / 1080P）。"
```

**Step 4: Update the `gying_check_updates` tool description in 可用工具 section**

Replace line 15:

```markdown
- `gying_check_updates`: 检查 gying.org 最新影片更新（支持定时任务和用户主动查询）
```

**Step 5: Run all tests to verify no regressions**

Run: `pytest tests/ -v`

Expected: All 75 tests pass (SKILL.md changes don't affect unit tests).

**Step 6: Commit**

```bash
git add nanobot/skills/film-download/SKILL.md
git commit -m "feat: enforce tool calls in film skill, add manual update trigger

- Add strict rules prohibiting LLM from fabricating download links
- Expand Scenario B to trigger on user phrases like '最新电影'
- Update quality filter description for tab-based filtering"
```

---

### Task 5: Final verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v`

Expected: All 75 tests pass.

**Step 2: Lint check**

Run: `ruff check nanobot/agent/tools/integrations/gying/tool.py nanobot/skills/ tests/test_gying.py tests/integration/test_film_workflow.py`

Expected: No errors.

**Step 3: Verify SKILL.md loads correctly**

Run:
```bash
python -c "
from pathlib import Path
from nanobot.agent.skills import SkillsLoader
loader = SkillsLoader(Path.home() / '.nanobot' / 'workspace')
skills = loader.get_always_skills()
print(f'Always-loaded skills: {[s.name for s in skills]}')
for s in skills:
    if s.name == 'film-download':
        print(f'Skill content length: {len(s.content)} chars')
        assert '严禁跳过工具调用' in s.content
        assert '最新电影' in s.content
        print('Enforcement text found OK')
"
```

Expected: `film-download` skill loaded with enforcement text present.
