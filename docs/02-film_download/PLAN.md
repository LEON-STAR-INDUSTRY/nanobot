# Film Download Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an automated film discovery + cloud download pipeline that integrates gying.org scraping and 115.com offline download into nanobot, with Feishu as the user interface.

**Architecture:** Two tools (`GyingScraperTool` for browser-based scraping, `Cloud115Tool` for API-based cloud storage), one orchestration skill (`film-download`), and cron integration for push notifications. Tools communicate via the existing `ToolRegistry`; state persists via JSON files.

**Tech Stack:** Playwright (gying.org SPA), p115client/py115 (115.com API), Pydantic v2 (config), asyncio (async I/O), pytest (testing)

---

## Phase 0: Spike Tests — Validate Core Uncertainties

### Task 1: Spike U1 — 115 API Library Validation

> Validate that a Python library can complete the full 115.com QR login → session save → magnet add cycle via HTTP API (no browser).

**Files:**
- Create: `tests/spike/spike_115_api.py`
- Create: `tests/spike/output/` (output directory for QR images, session files)

**Step 1: Create output directory and spike script skeleton**

```python
# tests/spike/spike_115_api.py
"""
Spike U1: Validate 115.com API library for QR login + offline download.

Run: python tests/spike/spike_115_api.py
Prerequisites: pip install p115client  (or pip install py115)
"""
import asyncio
import json
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
SESSION_FILE = OUTPUT_DIR / "115_session.json"
QR_FILE = OUTPUT_DIR / "qr_115.png"

# Step 1: Detect available library
LIB = None
try:
    import p115client
    LIB = "p115client"
except ImportError:
    pass

if not LIB:
    try:
        import py115
        LIB = "py115"
    except ImportError:
        pass

if not LIB:
    print("[FAIL] No 115 library found. Install: pip install p115client OR pip install py115")
    sys.exit(1)

print(f"[INFO] Using library: {LIB}")
```

**Step 2: Implement QR code generation**

Extend the spike script with QR generation logic for whichever library is available. Save QR image to `tests/spike/output/qr_115.png`. Print instructions for manual scanning.

**Step 3: Implement login polling**

Poll login status every 2 seconds for up to 120 seconds. Handle states: waiting → scanned → confirmed → expired. On success, save credentials to `tests/spike/output/115_session.json`.

**Step 4: Implement session reload & validation**

Reload session from file. Call an authenticated API endpoint to verify the session is valid.

**Step 5: Implement add magnet task**

Use a test magnet link. Call the offline download API. Verify task appears in task list. Clean up by deleting the test task.

**Step 6: Run the spike test**

Run: `python tests/spike/spike_115_api.py`

Expected output:
```
[INFO] Using library: p115client / py115
[PASS/FAIL] QR generation: saved to output/qr_115.png
[PASS/FAIL] Login polling: completed in Xs
[PASS/FAIL] Session save/load: 115_session.json valid
[PASS/FAIL] Add magnet: task created
[PASS/FAIL] Session expiry detection: error raised correctly
```

**Step 7: Document findings**

Record in `docs/02-film_download/details/01-spike_u1_115_api.md`:
- Which library works
- QR code lifecycle (image format, poll interval, expiry time)
- Credential serialization format
- API error codes for: expired session, quota full, duplicate task

**Step 8: Commit**

```bash
git add tests/spike/spike_115_api.py tests/spike/output/.gitkeep
git add docs/02-film_download/details/01-spike_u1_115_api.md
git commit -m "spike: validate 115.com API library (QR login + offline download)"
```

---

### Task 2: Spike U2 — gying.org Playwright Scraping

> Validate that Playwright can render the gying.org SPA, handle authentication, and extract movie data (search results, detail page, download links, latest listing page).

**Files:**
- Create: `tests/spike/spike_gying_scrape.py`

**Step 1: Create spike script with browser launch**

```python
# tests/spike/spike_gying_scrape.py
"""
Spike U2: Validate Playwright can scrape gying.org SPA.

Run: python tests/spike/spike_gying_scrape.py
Prerequisites: pip install playwright playwright-stealth && playwright install chromium
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
BROWSER_DATA = OUTPUT_DIR / "gying_browser_data"
```

**Step 2: Implement browser launch with stealth**

Launch Chromium with `user_data_dir` for cookie persistence. Apply anti-detection measures (stealth plugin or manual `navigator.webdriver` removal). Navigate to `https://www.gying.org/`. Take screenshot. Detect: login page, Cloudflare challenge, or content.

**Step 3: Investigate and implement login flow**

Manually inspect gying.org's auth mechanism via DevTools. Implement the login flow (username/password, social login, or QR code). Save cookies via `context.storage_state()`.

**Step 4: Implement search**

Find the search input element. Type a known movie name (e.g., "星际穿越"). Wait for results. Extract list of result items (title, URL, thumbnail). Screenshot.

**Step 5: Implement detail page extraction**

Navigate to first search result. Extract: title, rating, genres, actors, synopsis, poster URL. Screenshot. Document all CSS selectors used.

**Step 6: Implement download links extraction**

Find the download section on the detail page. Extract all download links with labels. Apply filter: 4K+中字 and 1080P+中字. Verify magnet link format.

**Step 7: Implement latest/trending listing page scraping (Scenario B)**

Navigate to the homepage or "latest releases" page. Extract movie listing items (title, URL, rating, thumbnail, date). Verify items have stable unique identifiers for dedup. Document listing page URL and selectors.

**Step 8: Save selectors to JSON**

Output all discovered CSS selectors to `tests/spike/output/selectors.json`:
```json
{
  "search_input": "...",
  "result_items": "...",
  "detail_title": "...",
  "detail_rating": "...",
  "detail_genres": "...",
  "detail_actors": "...",
  "detail_synopsis": "...",
  "detail_poster": "...",
  "download_section": "...",
  "download_rows": "...",
  "magnet_link": "...",
  "listing_items": "...",
  "listing_title": "...",
  "listing_url": "...",
  "listing_rating": "..."
}
```

**Step 9: Run the spike test**

Run: `python tests/spike/spike_gying_scrape.py`

Expected output:
```
[PASS/FAIL] Browser launch + stealth
[PASS/FAIL] Page renders (not empty HTML)
[PASS/FAIL] Login: authenticated
[PASS/FAIL] Search: found N results for "星际穿越"
[PASS/FAIL] Detail: title="星际穿越", rating="9.4"
[PASS/FAIL] Links: found N total, M×4K中字, K×1080P中字
[PASS/FAIL] Latest listing: found N movies on latest page
[INFO] Selectors saved to output/selectors.json
```

**Step 10: Document findings**

Record in `docs/02-film_download/details/02-spike_u2_gying_scrape.md`:
- Login mechanism discovered
- All CSS selectors with stability assessment
- Anti-bot detection encountered
- Magnet link format and container structure
- Listing page URL and pagination mechanism

**Step 11: Commit**

```bash
git add tests/spike/spike_gying_scrape.py tests/spike/output/selectors.json
git add docs/02-film_download/details/02-spike_u2_gying_scrape.md
git commit -m "spike: validate Playwright scraping of gying.org SPA"
```

---

### Task 3: Spike U3 — Multi-Turn Stateful Conversation

> Validate that nanobot's session + tool system can support a 5-turn stateful film-download workflow without losing context.

**Files:**
- Create: `tests/spike/spike_multi_turn.py`

**Step 1: Write mock tools**

Create `MockGyingTool` and `MockCloud115Tool` that return hardcoded data and use file-based state persistence (JSON):
- `MockGyingTool`: action=search returns hardcoded results; action=detail returns movie info; action=links returns magnet links
- `MockCloud115Tool`: action=check_session reads state file; action=login writes QR state; action=add_magnet returns success

**Step 2: Set up AgentLoop with mock tools**

Instantiate `AgentLoop` with mock tools registered. Use a test LLM provider (or real provider with a cheap model).

**Step 3: Simulate 5-turn conversation**

```
Turn 1: "帮我找 星际穿越"     → expect search results
Turn 2: "1"                   → expect movie detail (agent interprets "1" from context)
Turn 3: "4K"                  → expect links + login check
Turn 4: "已扫码"              → expect login confirmation
Turn 5: "1"                   → expect download confirmation
```

Verify each turn preserves context from previous turns.

**Step 4: Verify state persistence**

Check that state file contains expected data after each turn. Check session JSONL file contains all exchanges.

**Step 5: Run the spike test**

Run: `python tests/spike/spike_multi_turn.py`

Expected output:
```
[PASS/FAIL] Turn 1: Search results returned, session saved
[PASS/FAIL] Turn 2: Agent connected "1" to search results
[PASS/FAIL] Turn 3: Links fetched, login check triggered
[PASS/FAIL] Turn 4: Login confirmed
[PASS/FAIL] Turn 5: Download task added with correct magnet URL
```

**Step 6: Document findings**

Record in `docs/02-film_download/details/03-spike_u3_multi_turn.md`:
- Context window behavior across turns
- Whether short replies ("1", "4K") are interpreted correctly
- State persistence mechanism that works best
- Token usage across 5 turns

**Step 7: Commit**

```bash
git add tests/spike/spike_multi_turn.py
git add docs/02-film_download/details/03-spike_u3_multi_turn.md
git commit -m "spike: validate multi-turn stateful conversation flow"
```

---

### Task 4: Spike U4 — Cron Push → Feishu Reply Flow

> Validate that cron can push a message to Feishu and the user's reply shares session context with the push.

**Files:**
- Create: `tests/spike/spike_cron_push.py`

**Step 1: Write test script**

Create a script that starts the nanobot gateway with Feishu channel, creates a one-time cron job, waits for the push to fire, then verifies the user's reply shares session context.

**Step 2: Configure cron job**

```python
# Create cron job targeting specific Feishu user
job = {
    "name": "test-push",
    "message": "测试推送：1. 选项A  2. 选项B  3. 选项C\n请回复序号",
    "deliver": True,
    "channel": "feishu",
    "to": "{test_chat_id}"
}
```

**Step 3: Verify push delivery**

Wait for cron to fire. Check Feishu chat for the push message. Verify message format.

**Step 4: Verify reply session continuity**

User replies "2" in Feishu. Check that session file contains both push message and reply. Verify agent interprets "2" correctly from context.

**Step 5: Run the spike test**

Run: `python tests/spike/spike_cron_push.py`

Note: This requires a running Feishu channel and a real Feishu test account.

**Step 6: Document findings**

Record in `docs/02-film_download/details/04-spike_u4_cron_push.md`:
- `deliver=true` behavior
- Session key compatibility
- Latency between cron fire and Feishu delivery
- Whether `process_direct` response is saved to session before user replies

**Step 7: Commit**

```bash
git add tests/spike/spike_cron_push.py
git add docs/02-film_download/details/04-spike_u4_cron_push.md
git commit -m "spike: validate cron push to Feishu with session continuity"
```

---

## Phase 1: Core Tools — Scenario A Foundation

> Implementation only begins after relevant spikes pass their exit criteria.

### Task 5: Add Config Schema for Cloud115 and Gying

> Add Pydantic v2 config models for 115.com and gying.org integration settings.

**Files:**
- Modify: `nanobot/config/schema.py`
- Test: `tests/test_config_schema.py` (add test cases)

**Step 1: Write the failing test**

```python
# tests/test_config_schema.py (append)
def test_cloud115_config_defaults():
    from nanobot.config.schema import Cloud115Config
    cfg = Cloud115Config()
    assert cfg.enabled is False
    assert cfg.session_path == ""
    assert cfg.default_save_path == "/"

def test_gying_config_defaults():
    from nanobot.config.schema import GyingConfig
    cfg = GyingConfig()
    assert cfg.enabled is False
    assert cfg.headless is True
    assert cfg.check_schedule == "0 9 * * *"

def test_config_has_integrations():
    from nanobot.config.schema import Config
    cfg = Config()
    assert hasattr(cfg, 'integrations')
    assert hasattr(cfg.integrations, 'cloud115')
    assert hasattr(cfg.integrations, 'gying')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_schema.py -v`
Expected: FAIL with "cannot import name 'Cloud115Config'"

**Step 3: Write minimal implementation**

Add to `nanobot/config/schema.py`:

```python
class Cloud115Config(BaseModel):
    """115.com cloud storage configuration."""
    enabled: bool = False
    session_path: str = ""  # Default: ~/.nanobot/cloud115_session.json
    default_save_path: str = "/"  # Default 115 folder for downloads

class GyingConfig(BaseModel):
    """gying.org scraper configuration."""
    enabled: bool = False
    browser_data_dir: str = ""  # Default: ~/.nanobot/browser_data/gying/
    headless: bool = True
    check_schedule: str = "0 9 * * *"
    notify_channel: str = "feishu"
    notify_to: str = ""

class IntegrationsConfig(BaseModel):
    """Third-party integrations configuration."""
    cloud115: Cloud115Config = Field(default_factory=Cloud115Config)
    gying: GyingConfig = Field(default_factory=GyingConfig)
```

Add `integrations` field to `Config` class:
```python
class Config(BaseSettings):
    # ... existing fields ...
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_schema.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `pytest`
Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add nanobot/config/schema.py tests/test_config_schema.py
git commit -m "feat: add Cloud115Config and GyingConfig to schema"
```

---

### Task 6: Implement Cloud115Tool

> Wrap the validated 115.com API library (from Spike U1) into a nanobot Tool.

**Files:**
- Create: `nanobot/agent/tools/cloud115.py`
- Create: `tests/test_cloud115.py`

**Step 1: Write the failing test (mocked)**

```python
# tests/test_cloud115.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_cloud115_check_session_no_session():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool(session_path="/tmp/nonexistent.json")
    result = await tool.execute(action="check_session")
    data = json.loads(result)
    assert data["logged_in"] is False

@pytest.mark.asyncio
async def test_cloud115_tool_interface():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool()
    assert tool.name == "cloud115"
    assert "action" in tool.parameters["properties"]
    assert "login" in tool.parameters["properties"]["action"]["enum"]
    assert "add_magnet" in tool.parameters["properties"]["action"]["enum"]

@pytest.mark.asyncio
async def test_cloud115_add_magnet_not_logged_in():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool(session_path="/tmp/nonexistent.json")
    result = await tool.execute(action="add_magnet", magnet_url="magnet:?xt=urn:btih:test")
    assert "未登录" in result or "not logged in" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cloud115.py -v`
Expected: FAIL with "No module named 'nanobot.agent.tools.cloud115'"

**Step 3: Write implementation**

Create `nanobot/agent/tools/cloud115.py`:
- Class `Cloud115Tool(Tool)` with actions: `login`, `add_magnet`, `task_status`, `check_session`
- `login`: Generate QR code image bytes, return as base64 + instruction text. Save pending login state.
- `check_session`: Load session file, validate, return status.
- `add_magnet`: Load session, add magnet link via API, return confirmation.
- `task_status`: Query download task status.
- Use `asyncio.to_thread()` if the library is sync-only.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cloud115.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/tools/cloud115.py tests/test_cloud115.py
git commit -m "feat: implement Cloud115Tool (115.com QR login + offline download)"
```

---

### Task 7: Implement GyingScraperTool

> Wrap the validated Playwright scraping logic (from Spike U2) into a nanobot Tool.

**Files:**
- Create: `nanobot/agent/tools/gying.py`
- Create: `tests/test_gying.py`

**Step 1: Write the failing test (mocked)**

```python
# tests/test_gying.py
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_gying_tool_interface():
    from nanobot.agent.tools.gying import GyingScraperTool
    tool = GyingScraperTool()
    assert tool.name == "gying_search"
    assert "action" in tool.parameters["properties"]
    assert set(tool.parameters["properties"]["action"]["enum"]) == {"search", "detail", "links"}

@pytest.mark.asyncio
async def test_gying_search_returns_json():
    from nanobot.agent.tools.gying import GyingScraperTool
    tool = GyingScraperTool()
    # Mock the internal browser call
    with patch.object(tool, '_search', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"title": "星际穿越 Interstellar (2014)", "url": "https://gying.org/movie/123", "rating": "9.4"}
        ]
        result = await tool.execute(action="search", query="星际穿越")
        data = json.loads(result)
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["title"] == "星际穿越 Interstellar (2014)"

@pytest.mark.asyncio
async def test_gying_search_requires_query():
    from nanobot.agent.tools.gying import GyingScraperTool
    tool = GyingScraperTool()
    result = await tool.execute(action="search")
    assert "error" in result.lower() or "query" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gying.py -v`
Expected: FAIL with "No module named 'nanobot.agent.tools.gying'"

**Step 3: Write implementation**

Create `nanobot/agent/tools/gying.py`:
- Class `GyingScraperTool(Tool)` with actions: `search`, `detail`, `links`
- Lazy browser launch on first call. Cookie persistence via `user_data_dir`.
- Selectors loaded from config or constants (based on Spike U2 findings).
- All internal methods are async: `_search()`, `_detail()`, `_links()`.
- Return structured JSON strings.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gying.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/tools/gying.py tests/test_gying.py
git commit -m "feat: implement GyingScraperTool (Playwright-based gying.org scraper)"
```

---

### Task 8: Register Tools in AgentLoop

> Conditionally register Cloud115Tool and GyingScraperTool based on config.

**Files:**
- Modify: `nanobot/agent/loop.py`
- Test: `tests/test_tool_registration.py`

**Step 1: Write the failing test**

```python
# tests/test_tool_registration.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

@pytest.mark.asyncio
async def test_gying_tool_registered_when_enabled():
    from nanobot.agent.loop import AgentLoop
    from nanobot.config.schema import Config
    # Create config with gying enabled
    config = Config()
    config.integrations.gying.enabled = True
    # ... setup AgentLoop with config ...
    # assert loop.tools.has("gying_search")

@pytest.mark.asyncio
async def test_gying_tool_not_registered_when_disabled():
    # ... config with gying.enabled = False ...
    # assert not loop.tools.has("gying_search")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_tool_registration.py -v`
Expected: FAIL

**Step 3: Write implementation**

Modify `_register_default_tools()` in `nanobot/agent/loop.py`:

```python
def _register_default_tools(self) -> None:
    # ... existing tool registrations ...

    # Film download tools (conditional on config)
    if self.config and self.config.integrations.gying.enabled:
        from nanobot.agent.tools.gying import GyingScraperTool
        gying_config = self.config.integrations.gying
        self.tools.register(GyingScraperTool(
            browser_data_dir=gying_config.browser_data_dir,
            headless=gying_config.headless,
        ))

    if self.config and self.config.integrations.cloud115.enabled:
        from nanobot.agent.tools.cloud115 import Cloud115Tool
        cloud115_config = self.config.integrations.cloud115
        self.tools.register(Cloud115Tool(
            session_path=cloud115_config.session_path,
            default_save_path=cloud115_config.default_save_path,
        ))
```

Note: `AgentLoop.__init__` needs a `config` parameter. Check the existing constructor and how it's instantiated in `cli/commands.py` or gateway setup.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_tool_registration.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `pytest`
Expected: All tests pass

**Step 6: Commit**

```bash
git add nanobot/agent/loop.py tests/test_tool_registration.py
git commit -m "feat: conditionally register Cloud115Tool and GyingScraperTool"
```

---

## Phase 2: Skill & Multi-Turn Integration — Scenario A Complete

### Task 9: Create Film Download Skill

> Write the orchestration skill that teaches the agent the complete film download workflow for Scenario A and B.

**Files:**
- Create: `nanobot/skills/film-download/SKILL.md`

**Step 1: Write the skill markdown**

Create `nanobot/skills/film-download/SKILL.md` with:
- YAML frontmatter: name, description, always_load: true
- Scenario A workflow (search → detail → links → login → download)
- Scenario B workflow (cron trigger → check updates → notify → user reply → continue as A)
- Error handling instructions
- Response format examples (Chinese)

Use the content from DESIGN.md Section 3.4 as the template, refined with actual selector/format details from spikes.

**Step 2: Verify skill loads**

Run: `python -c "from nanobot.agent.skills import SkillsLoader; s = SkillsLoader(Path('~/.nanobot/workspace').expanduser()); print(s.load_skill('film-download'))"`

Expected: Skill content printed without errors.

**Step 3: Commit**

```bash
git add nanobot/skills/film-download/SKILL.md
git commit -m "feat: add film-download orchestration skill"
```

---

### Task 10: Implement QR Login Multi-Turn Flow

> Refine Cloud115Tool's login action to work as a multi-turn interaction: generate QR (Turn N) → user scans → confirm (Turn N+1).

**Files:**
- Modify: `nanobot/agent/tools/cloud115.py`
- Modify: `tests/test_cloud115.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_cloud115_login_generates_qr():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool()
    # Mock library to return QR bytes
    with patch.object(tool, '_generate_qr', new_callable=AsyncMock) as mock_qr:
        mock_qr.return_value = (b'\x89PNG...', "token123")
        result = await tool.execute(action="login")
        data = json.loads(result)
        assert "qr_image_base64" in data
        assert "instruction" in data
        assert data["status"] == "waiting_for_scan"

@pytest.mark.asyncio
async def test_cloud115_confirm_login_checks_status():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool()
    with patch.object(tool, '_check_login_status', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"status": "confirmed", "session": {...}}
        result = await tool.execute(action="check_session")
        data = json.loads(result)
        assert data["logged_in"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cloud115.py::test_cloud115_login_generates_qr -v`
Expected: FAIL

**Step 3: Implement login state machine**

Split `login` action into:
1. `action="login"`: Generate QR, save state to `~/.nanobot/cloud115_login_state.json`, return QR image + instructions
2. `action="check_session"`: If login state exists and is pending, poll 115 API for login confirmation. On success, save session and clean up login state.

This allows the agent to:
- Call `login` → get QR → send to user via Feishu
- Next turn, call `check_session` → detect login success → proceed

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cloud115.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/tools/cloud115.py tests/test_cloud115.py
git commit -m "feat: implement multi-turn QR login flow for Cloud115Tool"
```

---

### Task 11: Scenario A Integration Test

> End-to-end manual test of the complete Scenario A workflow via Feishu.

**Files:**
- Create: `tests/integration/test_film_workflow.py`

**Step 1: Write integration test script**

Script that automates the 5-turn conversation through the actual AgentLoop with real tools (or semi-mocked with real Feishu).

**Step 2: Run manually**

Start nanobot gateway. Send "帮我找 星际穿越" via Feishu. Complete the full flow.

**Step 3: Document results**

Record in `docs/02-film_download/details/05-scenario_a_integration.md`:
- Each turn's input/output
- Screenshots of Feishu conversation
- Issues encountered and fixes applied
- Total time and token usage

**Step 4: Commit**

```bash
git add tests/integration/test_film_workflow.py
git add docs/02-film_download/details/05-scenario_a_integration.md
git commit -m "test: Scenario A integration test + documentation"
```

---

## Phase 3: Scheduled Push — Scenario B

### Task 12: Implement GyingUpdatesTool

> Build the tool that checks gying.org for new releases and compares against a local seen_movies.json.

**Files:**
- Modify: `nanobot/agent/tools/gying.py` (add GyingUpdatesTool class)
- Create: `tests/test_gying_updates.py`

**Step 1: Write the failing test**

```python
# tests/test_gying_updates.py
import pytest
import json
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_gying_updates_tool_interface():
    from nanobot.agent.tools.gying import GyingUpdatesTool
    tool = GyingUpdatesTool()
    assert tool.name == "gying_check_updates"
    assert "category" in tool.parameters["properties"]

@pytest.mark.asyncio
async def test_gying_updates_filters_seen():
    from nanobot.agent.tools.gying import GyingUpdatesTool
    tool = GyingUpdatesTool(seen_file="/tmp/test_seen.json")
    # Pre-populate seen file
    # Mock browser to return 3 movies, 1 already seen
    # Assert result contains only 2 new movies
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gying_updates.py -v`
Expected: FAIL

**Step 3: Implement GyingUpdatesTool**

Add to `nanobot/agent/tools/gying.py`:
- Class `GyingUpdatesTool(Tool)` with name `gying_check_updates`
- Shares browser instance with `GyingScraperTool`
- Reads `seen_movies.json`, scrapes listing page, diffs, returns new entries
- Writes new entries to `seen_movies.json` after notification

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gying_updates.py -v`
Expected: PASS

**Step 5: Register tool in AgentLoop**

Add conditional registration in `_register_default_tools()`.

**Step 6: Commit**

```bash
git add nanobot/agent/tools/gying.py tests/test_gying_updates.py nanobot/agent/loop.py
git commit -m "feat: implement GyingUpdatesTool for daily new release checks"
```

---

### Task 13: Configure Cron Job for Scenario B

> Set up the daily cron job that triggers the gying.org check and pushes results to Feishu.

**Files:**
- Modify: `nanobot/skills/film-download/SKILL.md` (add cron setup instructions)
- Test: Manual via nanobot CLI

**Step 1: Document cron setup in skill**

Add instructions for the agent to create the cron job when user says "每天帮我检查新片":

```
# In SKILL.md
## Setting Up Daily Checks
When user asks for daily checks, use the cron tool:
- name: "gying-daily-check"
- schedule: config value or "0 9 * * *"
- message: "检查 gying.org 最新影片更新，将新发现的影片通知我"
- deliver: true
- channel: feishu
- to: current chat_id
```

**Step 2: Test cron job creation**

Via CLI: `nanobot agent -m "每天早上9点帮我检查新片"`
Expected: Agent creates cron job using the cron tool.

**Step 3: Test cron job execution**

Wait for cron to fire (or trigger manually). Verify Feishu notification. Reply with a number. Verify conversation continues as Scenario A.

**Step 4: Document results**

Record in `docs/02-film_download/details/06-scenario_b_cron_setup.md`.

**Step 5: Commit**

```bash
git add nanobot/skills/film-download/SKILL.md
git add docs/02-film_download/details/06-scenario_b_cron_setup.md
git commit -m "feat: configure Scenario B cron job for daily gying.org checks"
```

---

## Phase 4: Polish & Hardening

### Task 14: Error Handling & Chinese UX

> Ensure all error messages are user-friendly Chinese text.

**Files:**
- Modify: `nanobot/agent/tools/cloud115.py`
- Modify: `nanobot/agent/tools/gying.py`
- Test: `tests/test_error_messages.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_gying_scrape_timeout_returns_chinese_error():
    from nanobot.agent.tools.gying import GyingScraperTool
    tool = GyingScraperTool()
    # Mock browser timeout
    with patch.object(tool, '_search', side_effect=TimeoutError("Page timeout")):
        result = await tool.execute(action="search", query="test")
        assert "抓取失败" in result or "超时" in result

@pytest.mark.asyncio
async def test_cloud115_session_expired_chinese():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool()
    # Mock expired session
    result = await tool.execute(action="add_magnet", magnet_url="magnet:?xt=test")
    assert "未登录" in result or "登录已过期" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_error_messages.py -v`
Expected: FAIL

**Step 3: Implement error handling**

Update both tools to catch exceptions and return Chinese error messages:
- `TimeoutError` → "抓取失败，网站可能已更新。请稍后重试。"
- `SessionExpired` → "115 登录已过期，请重新扫码登录。"
- `QuotaExceeded` → "115 空间不足，无法添加下载任务。"
- `NoMatchingLinks` → "未找到匹配的下载链接，显示所有可用链接："

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_error_messages.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/tools/cloud115.py nanobot/agent/tools/gying.py tests/test_error_messages.py
git commit -m "feat: add Chinese error messages for all failure modes"
```

---

### Task 15: Session Auto-Recovery for 115

> Detect 115 session expiry during operations and automatically trigger re-login.

**Files:**
- Modify: `nanobot/agent/tools/cloud115.py`
- Modify: `tests/test_cloud115.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_cloud115_auto_detect_expired_session():
    from nanobot.agent.tools.cloud115 import Cloud115Tool
    tool = Cloud115Tool()
    # Mock: session file exists but API returns 401/expired
    # Assert: tool returns re-login prompt instead of cryptic error
```

**Step 2: Run test, implement, verify**

Add session validation before each authenticated API call. If expired, return "115 登录已过期。请发送 '登录115' 重新扫码。"

**Step 3: Commit**

```bash
git add nanobot/agent/tools/cloud115.py tests/test_cloud115.py
git commit -m "feat: auto-detect 115 session expiry and prompt re-login"
```

---

### Task 16: Seen Movies Cleanup

> Auto-remove entries older than 90 days from seen_movies.json.

**Files:**
- Modify: `nanobot/agent/tools/gying.py`
- Add test in: `tests/test_gying_updates.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_seen_movies_cleanup_removes_old():
    # Create seen_movies.json with entries from 100 days ago and 10 days ago
    # Call cleanup
    # Assert old entries removed, recent entries preserved
```

**Step 2: Implement cleanup**

Add `_cleanup_seen_movies()` to GyingUpdatesTool. Call it after each `check_updates` execution. Remove entries where `first_seen` is older than 90 days.

**Step 3: Commit**

```bash
git add nanobot/agent/tools/gying.py tests/test_gying_updates.py
git commit -m "feat: auto-cleanup seen_movies.json entries older than 90 days"
```

---

### Task 17: Final Integration Test & Documentation

> Run full end-to-end test of both Scenario A and B. Write final summary.

**Files:**
- Create: `docs/02-film_download/details/07-final_integration.md`

**Step 1: Run full test suite**

Run: `pytest -v`
Expected: All tests pass.

**Step 2: Run lint**

Run: `ruff check nanobot/ tests/`
Expected: No errors.

**Step 3: Run Scenario A manually**

Via Feishu: Complete the full search → detail → links → login → download flow.

**Step 4: Run Scenario B manually**

Set up cron job. Wait for push. Reply with selection. Complete download.

**Step 5: Document everything**

Record in `docs/02-film_download/details/07-final_integration.md`:
- Test results summary
- Known limitations
- Future improvements
- Files changed inventory

**Step 6: Update docs/README.md**

Add PLAN.md and all detail documents to the master index.

**Step 7: Final commit**

```bash
git add docs/
git commit -m "docs: final integration test results and documentation"
```

---

## Task Summary & Dependencies

```
Phase 0: Spike Tests (can run in parallel)
  Task 1: Spike U1 — 115 API Library
  Task 2: Spike U2 — gying.org Playwright
  Task 3: Spike U3 — Multi-Turn Flow
  Task 4: Spike U4 — Cron Push to Feishu

Phase 1: Core Tools (sequential, depends on Phase 0)
  Task 5: Config Schema          ← no spike dependency
  Task 6: Cloud115Tool           ← depends on Task 1 (U1)
  Task 7: GyingScraperTool       ← depends on Task 2 (U2)
  Task 8: Register Tools         ← depends on Task 5, 6, 7

Phase 2: Skill & Integration (sequential, depends on Phase 1)
  Task 9: Film Download Skill    ← depends on Task 6, 7
  Task 10: QR Login Multi-Turn   ← depends on Task 3 (U3), Task 6
  Task 11: Scenario A Test       ← depends on Task 8, 9, 10

Phase 3: Scenario B (depends on Phase 2)
  Task 12: GyingUpdatesTool      ← depends on Task 7, Task 2 (U2)
  Task 13: Cron Job Setup        ← depends on Task 4 (U4), Task 12

Phase 4: Polish (depends on Phase 2+3)
  Task 14: Error Handling        ← depends on Task 6, 7
  Task 15: Session Auto-Recovery ← depends on Task 6
  Task 16: Seen Movies Cleanup   ← depends on Task 12
  Task 17: Final Integration     ← depends on all above
```

## Summary Document Convention

After completing each module-level task, create a summary document at:

```
docs/02-film_download/details/{序号}-{任务名称}.md
```

Format follows the standard document format (Universal Header):

```markdown
# DOCUMENT METADATA
title: {任务名称} - Summary
filename: {序号}-{任务名称}.md
status: Approved
version: 1.0.0
owner: AI Assistant
last_updated: {YYYY-MM-DD}
---

## Document History
| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0.0   | ...  | Claude | Initial creation       |

## Purpose & Scope
> Summary of Task N completion.

---

## Implementation Summary
...

## Files Changed
...

## Test Results
...

## Issues & Notes
...
```

Expected detail documents:
1. `01-spike_u1_115_api.md` — 115 API library validation results
2. `02-spike_u2_gying_scrape.md` — gying.org scraping validation results
3. `03-spike_u3_multi_turn.md` — Multi-turn conversation flow results
4. `04-spike_u4_cron_push.md` — Cron push to Feishu results
5. `05-scenario_a_integration.md` — Scenario A end-to-end test results
6. `06-scenario_b_cron_setup.md` — Scenario B cron configuration results
7. `07-final_integration.md` — Final integration test and documentation
