# DOCUMENT METADATA
title: Film Download Feature - System Design
filename: DESIGN.md
status: Draft
version: 1.2.0
owner: AI Assistant / User
last_updated: 2026-02-11
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-11 | Claude | Initial creation based on README.md research report |
| 1.1.0   | 2026-02-11 | Claude | Added Phase 0 spike test specifications for three core uncertainties |
| 1.2.0   | 2026-02-11 | Claude | Added Scenario B (scheduled push), cron integration, update tracking module |

## Purpose & Scope
> Design document for integrating automated film discovery (gying.org) and cloud storage download (115.com) capabilities into the nanobot framework via Feishu channel interaction. This document defines the architecture, module interfaces, implementation phases, and test strategy.

---

## 1. Feature Overview

### 1.1 Goal
Enable two complementary modes of film discovery and cloud download via Feishu:
- **Scenario A (Pull)**: User asks for a specific movie → agent searches, presents info, downloads on demand.
- **Scenario B (Push)**: Agent periodically checks gying.org for new releases → pushes discoveries to Feishu → user selects and downloads.

Both scenarios share the same gying.org scraping tools and 115.com download tools. They differ only in the trigger mechanism and the initial conversation flow.

### 1.2 Scenario A: User-Initiated Search (Pull)

```
User: "帮我找一下 星际穿越"
  → Agent calls gying_search tool → scrapes gying.org → returns movie info
  → Agent sends formatted movie card (title, rating, poster, synopsis)
  → Agent asks: "是否需要下载？请回复 '4K' 或 '1080P'"

User: "4K"
  → Agent calls gying_links tool → fetches download links, filters for 4K+中字
  → Agent presents link options as numbered list
  → Agent asks: "请选择下载链接（回复序号）"

User: "1"
  → Agent calls cloud115_download tool → adds magnet to 115 offline download
  → Agent confirms: "已添加离线下载任务: [filename]"
```

### 1.3 Scenario B: Scheduled Discovery (Push)

```
[Cron job fires daily at 09:00]
  → Agent calls gying_check_updates tool → scrapes gying.org latest/trending page
  → Agent compares against local seen_movies.json → filters out already-notified movies
  → Agent sends message to Feishu via deliver=true:

    "发现 3 部新影片：
     1. 沙丘3 Dune: Part Three (2026) ⭐ 8.7
     2. 黑暗骑士归来 (2026) ⭐ 9.1
     3. 流浪地球3 (2026) ⭐ 8.3

     回复序号查看详情并下载"

User: "2"
  → Agent loads update context from state file
  → Agent calls gying_search(action="detail") → shows full movie info
  → Conversation continues as Scenario A from "是否需要下载？" onward
```

**Key mechanism**: Nanobot's cron system (`CronService`) supports `deliver=true` which sends the agent's response directly to a Feishu user/chat. The user's reply enters the normal message flow, and session history ensures context continuity.

### 1.4 Scenario Comparison

| Aspect | Scenario A (Pull) | Scenario B (Push) |
|--------|-------------------|-------------------|
| Trigger | User sends message | Cron job fires on schedule |
| Entry point | User query text | Cron payload: "check gying.org for updates" |
| gying.org action | Search by keyword | Browse latest/trending page |
| New state needed | None | `seen_movies.json` (dedup), cron job config |
| Tools reused | gying_search, cloud115 | gying_search, cloud115 + **gying_check_updates** (new) |
| Feishu delivery | Normal response | `deliver=true` via cron |
| Session key | `feishu:{chat_id}` | `feishu:{chat_id}` (same, enables reply continuity) |

### 1.5 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| gying.org scraping | Playwright (headless) | Site is a full SPA (client-side rendered with proprietary `_BT` framework). Server returns empty HTML. HTTP+BeautifulSoup returns zero content. |
| 115.com integration | Python API library (p115client > py115 > Playwright fallback) | 115.com has well-documented HTTP APIs. Libraries provide QR login + offline download without browser binaries. **Requires validation testing before commitment.** |
| User interaction model | Text-based commands (not Feishu card callbacks) | Card action callbacks require a webhook HTTP server. Current nanobot Feishu channel uses WebSocket only. Text commands work without infrastructure changes. |
| Feishu message format | Rich text cards (display only, no interactive buttons) | Cards for structured display (poster, rating, metadata). User actions via text replies. |
| Scheduled trigger | Nanobot CronService with `deliver=true` | Built-in cron system already supports agent-initiated messages to Feishu. No new infrastructure needed. |
| Update dedup | Local `seen_movies.json` file | Simple file-based tracking. Agent writes movie IDs after notifying user. Prevents duplicate push notifications. |

---

## 2. Architecture

### 2.1 Component Overview

```
                    ┌──────────────────┐
                    │   CronService    │  Scenario B trigger
                    │  (daily 09:00)   │
                    └────────┬─────────┘
                             │ process_direct()
                             ↓
Feishu User ──────→ FeishuChannel ──────→ MessageBus ──────→ AgentLoop
  (text msg)        (WebSocket)            (async queue)       │
                         ↑                                     │
                         │ deliver=true                        │
                         │ (OutboundMessage)                   │
                         │                                     │
                    ┌────┴──────────────────────────────────────┘
                    │
                    ├── Skill: film-download (SKILL.md)
                    │
                    ├── Tool: gying_search         ← Playwright (search, detail, links)
                    ├── Tool: gying_check_updates   ← Playwright (browse latest, compare seen_movies)
                    ├── Tool: cloud115_login        ← py115/p115client API (QR auth)
                    ├── Tool: cloud115_download     ← py115/p115client API (add magnet)
                    └── Tool: cloud115_status       ← py115/p115client API (task status)
```

### 2.2 Scenario B: Cron → Agent → Feishu Flow

```
CronService._execute_job()
  → on_cron_job(job) callback
    → agent.process_direct(
        message="检查 gying.org 最新影片更新，对比 seen_movies.json，将新发现的影片通过飞书通知用户",
        session_key="feishu:{user_open_id}",   # Same as user's chat session
        channel="feishu",
        chat_id="{user_open_id}"
      )
    → Agent executes gying_check_updates tool
    → Agent formats results, uses message tool to send to user
    → deliver=true → OutboundMessage → FeishuChannel.send()
    → User receives notification in Feishu

User replies "2"
  → Normal FeishuChannel._on_message() → InboundMessage
  → Same session_key "feishu:{user_open_id}" → session history includes the push message
  → Agent sees context: "I sent a list of 3 movies, user replied '2'"
  → Continues as Scenario A
```

**Critical detail**: The cron job's `session_key` MUST match the user's normal Feishu session key (`feishu:{chat_id}`). This ensures the push notification and the user's reply share the same conversation history.

### 2.3 Module Responsibilities

| Module | Type | Responsibility | Used In |
|--------|------|---------------|---------|
| `film-download` skill | Skill (SKILL.md) | Orchestration prompt for both scenarios | A + B |
| `GyingScraperTool` | Tool | Search, detail, links extraction from gying.org | A + B |
| `GyingUpdatesTool` | Tool | Browse latest/trending, compare against seen list | B only |
| `Cloud115Tool` | Tool | 115.com API: login, add magnet, check status | A + B |

### 2.4 Why Two Separate Tools (not one)

- **Separation of concerns**: gying.org scraping (browser-based) and 115.com API (HTTP-based) have completely different dependency stacks and failure modes.
- **Independent testability**: Each tool can be validated in isolation.
- **Reusability**: The 115 tool can be used for any download source in the future, not just gying.org.

---

## 3. Module Design

### 3.1 Module A: Gying Scraper Tool

**File**: `nanobot/agent/tools/gying.py`

**Tool Interface**:
```python
class GyingScraperTool(Tool):
    name = "gying_search"
    description = "Search for a movie on gying.org and return structured info + download links"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Movie name to search for"},
            "action": {
                "type": "string",
                "enum": ["search", "detail", "links"],
                "description": "search=find movie, detail=get info, links=get download links"
            },
            "url": {"type": "string", "description": "Movie detail page URL (for detail/links action)"},
            "resolution": {
                "type": "string",
                "enum": ["4K", "1080P", "all"],
                "description": "Filter download links by resolution"
            }
        },
        "required": ["action"]
    }
```

**Return format (search)**:
```json
{
  "results": [
    {"title": "星际穿越 Interstellar (2014)", "url": "https://gying.org/movie/123", "rating": "9.4"}
  ]
}
```

**Return format (detail)**:
```json
{
  "title": "星际穿越 Interstellar",
  "year": "2014",
  "rating": "9.4",
  "genres": ["科幻", "冒险", "剧情"],
  "actors": ["马修·麦康纳", "安妮·海瑟薇"],
  "synopsis": "...",
  "poster_url": "https://...",
  "source_url": "https://gying.org/movie/123"
}
```

**Return format (links)**:
```json
{
  "links": [
    {
      "label": "[4K] Interstellar.2014.2160p.UHD.BluRay.中字",
      "magnet": "magnet:?xt=urn:btih:...",
      "size": "45.2 GB",
      "resolution": "4K"
    }
  ]
}
```

**Browser lifecycle**:
- Playwright browser launched lazily on first tool call.
- Browser context persisted across calls within the same agent session (for login state).
- Browser user data dir: `~/.nanobot/browser_data/gying/` (cookie persistence across restarts).
- `playwright-stealth` or equivalent anti-detection measures applied.

**gying.org login handling**:
- gying.org requires authentication. The tool must handle login.
- **Phase 0 (reconnaissance)**: Before implementation, manually inspect gying.org's login flow and internal API endpoints via DevTools.
- The exact login mechanism (username/password, social login, invite-only) needs manual investigation.
- If QR code login is available, use the same HVR pattern as 115.

**CSS selector strategy**:
- All selectors are TBD — must be determined during Phase 0 reconnaissance.
- The README.md's selector table (`.movie-title`, `.score-num`, etc.) is speculative and based on generic assumptions. **Do not use these without validation.**
- Document actual selectors in a separate `SELECTORS.md` after reconnaissance.

### 3.2 Module B: Cloud 115 Tool

**File**: `nanobot/agent/tools/cloud115.py`

**Tool Interface**:
```python
class Cloud115Tool(Tool):
    name = "cloud115"
    description = "Manage 115.com cloud storage: login via QR code, add offline download tasks"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["login", "add_magnet", "task_status", "check_session"],
                "description": "login=QR code login, add_magnet=add download task, task_status=check tasks, check_session=verify if logged in"
            },
            "magnet_url": {"type": "string", "description": "Magnet link for add_magnet action"},
            "save_path": {"type": "string", "description": "115 folder path to save downloaded files"}
        },
        "required": ["action"]
    }
```

**Login flow (API-based, no browser)**:
```
1. Tool calls cloud115_login action
2. Library generates QR code image bytes via HTTP API
3. Tool returns image as base64 + instruction text
4. Agent sends QR image to user via Feishu (using existing image send capability)
5. User scans with 115 mobile app
6. Tool polls login status via HTTP API (timeout: 120s)
7. On success: save credentials to ~/.nanobot/cloud115_session.json
8. Return "登录成功"
```

**Session persistence**:
- Credentials (cookies/tokens) stored at `~/.nanobot/cloud115_session.json`.
- On each tool call, attempt to load existing session first.
- If session expired or invalid, prompt re-login automatically.

**Library selection (to be validated in Phase 0)**:

| Priority | Library | Python | Notes |
|----------|---------|--------|-------|
| 1st | p115client | >= 3.12 | Most comprehensive, async support. Test if project can use Python 3.12+. |
| 2nd | py115 | >= 3.10 | Clean API, proven stable. Sync but wrappable with `asyncio.to_thread()`. |
| 3rd | Playwright | >= 3.11 | Fallback if neither library works. Browser-based, heaviest option. |

### 3.3 Module C: Gying Updates Tool (Scenario B)

**File**: `nanobot/agent/tools/gying.py` (same file as GyingScraperTool, shared browser instance)

**Tool Interface**:
```python
class GyingUpdatesTool(Tool):
    name = "gying_check_updates"
    description = "Check gying.org for new movie releases and return unseen ones"
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["latest", "trending", "4k", "all"],
                "description": "Which gying.org listing page to check"
            },
            "max_results": {
                "type": "integer",
                "description": "Max number of new movies to return",
                "default": 10
            }
        },
        "required": []
    }
```

**Return format**:
```json
{
  "new_movies": [
    {
      "title": "沙丘3 Dune: Part Three (2026)",
      "url": "https://gying.org/movie/456",
      "rating": "8.7",
      "thumbnail": "https://...",
      "added_date": "2026-02-11"
    }
  ],
  "total_checked": 30,
  "previously_seen": 27,
  "new_count": 3
}
```

**Deduplication logic**:
- Maintains `~/.nanobot/data/film_download/seen_movies.json`:
  ```json
  {
    "movies": {
      "https://gying.org/movie/123": {
        "title": "星际穿越",
        "first_seen": "2026-02-10",
        "notified": true
      }
    },
    "last_check": "2026-02-11T09:00:00"
  }
  ```
- On each call: scrape listing page → compare against seen list → return only new entries
- After notification sent: mark entries as `notified: true`
- File grows unbounded — add periodic cleanup (remove entries older than 90 days)

**gying.org listing pages (to be validated in Spike U2)**:
- The exact URL for "latest" or "trending" pages on gying.org needs investigation
- Likely candidates: homepage, a "latest" tab, or a "new releases" section
- Selector for listing items: TBD (same investigation as Spike U2)

### 3.4 Module D: Film Download Skill

**File**: `nanobot/skills/film-download/SKILL.md`

This is a markdown skill that teaches the agent the orchestration workflow for **both scenarios**:

```markdown
---
name: film-download
description: Search movies on gying.org and download to 115.com cloud storage
always_load: true
---

# Film Download Workflow

## Available Tools
- `gying_search`: Search and scrape movie information from gying.org
- `gying_check_updates`: Check gying.org for new releases (used by cron)
- `cloud115`: Manage 115.com cloud storage (login, download, status)

## Scenario A: User Searches for a Movie

### Step 1: Search Movie
When user asks to find/download a movie:
1. Call `gying_search` with action="search" and the movie name
2. Present results as a numbered list with title, year, and rating
3. Ask user to select by number

### Step 2: Show Movie Details
1. Call `gying_search` with action="detail" and the selected URL
2. Format and display: title, rating, genres, actors, synopsis
3. If poster available, include image
4. Ask: "是否需要下载？回复 '4K' 或 '1080P'"

### Step 3: Get Download Links
1. Call `gying_search` with action="links", resolution=user's choice
2. Present filtered links as numbered list: [resolution] filename (size)
3. Ask user to select by number

### Step 4: Ensure 115 Login
1. Call `cloud115` with action="check_session"
2. If not logged in, call action="login" and send QR image to user
3. Wait for user to scan and confirm

### Step 5: Add Download Task
1. Call `cloud115` with action="add_magnet" and selected magnet link
2. Confirm success or report error

## Scenario B: Scheduled New Release Check

When triggered by cron job (message contains "检查 gying.org"):
1. Call `gying_check_updates` with category="latest"
2. If new_count == 0: reply "暂无新影片更新"
3. If new_count > 0: format as numbered list:
   "发现 N 部新影片：
    1. Title (Year) ⭐ Rating
    2. ...
    回复序号查看详情并下载"
4. When user replies with a number, look up the movie URL from the list
5. Continue from Scenario A Step 2 (show details)

## Error Handling
- If gying.org scraping fails: "抓取失败，网站可能已更新。请稍后重试。"
- If 115 session expired: auto-trigger re-login flow
- If 115 space insufficient: report the error message from 115
- If no matching resolution found: show all available links instead
- If cron check finds nothing new: reply "暂无新影片更新" (only logged, not sent to user)
```

### 3.5 Cron Job Configuration (Scenario B)

The cron job is set up once via the nanobot CLI or by the agent itself using the cron tool:

```bash
nanobot cron add \
  --name "gying-daily-check" \
  --message "检查 gying.org 最新影片更新，将新发现的影片通知我" \
  --cron "0 9 * * *" \
  --deliver \
  --channel feishu \
  --to "{user_open_id}"
```

Or the agent can create it when the user says "每天帮我检查新片":
```python
# Agent uses cron tool:
await cron_tool.execute(
    action="add",
    name="gying-daily-check",
    schedule="0 9 * * *",
    message="检查 gying.org 最新影片更新，将新发现的影片通知我",
    deliver=True,
    channel="feishu",
    to=current_chat_id,
)
```

**Session continuity**: The cron job uses `session_key=f"feishu:{user_open_id}"` which is the same as the user's normal Feishu chat session. This means:
- The push notification appears in the same conversation
- The user's reply merges into the same session history
- The agent has full context of what it pushed and what the user selected

---

## 4. Feishu Interaction Design

### 4.1 Message Format

Since we're using text-based interaction (no card callbacks), messages use Feishu's existing card rendering for display with text replies for input.

**Movie info display** (agent sends as rich text / markdown card):
```
🎬 星际穿越 Interstellar (2014)
⭐ 豆瓣评分: 9.4

类型: 科幻 / 冒险 / 剧情
主演: 马修·麦康纳, 安妮·海瑟薇, 杰西卡·查斯坦
简介: 在不远的未来，随着地球自然环境的恶化，人类面临着无法生存的威胁...

是否需要下载？回复 "4K" 或 "1080P"
```

**Download links display**:
```
找到以下 4K 中字资源:

1. [4K] Interstellar.2014.2160p.BluRay.REMUX.中英字幕 (45.2 GB)
2. [4K] Interstellar.2014.2160p.HDR.WEB-DL.中字 (18.7 GB)

请回复序号选择下载
```

### 4.2 Image Handling

The gying scraper may return a poster URL. The agent can use the existing `web_fetch` tool to download the poster, then include it in the Feishu message. The Feishu channel already supports sending images.

For 115 QR code login, the tool returns base64 image data. The agent sends this as an image message through the standard message flow.

---

## 5. Configuration

### 5.1 Config Schema Addition

Add to `nanobot/config/schema.py`:

```python
class Cloud115Config(BaseSettings):
    """115.com cloud storage configuration"""
    enabled: bool = False
    session_path: str = ""  # Path to session file, default: ~/.nanobot/cloud115_session.json
    default_save_path: str = "/"  # Default 115 folder for downloads

class GyingConfig(BaseSettings):
    """gying.org scraper configuration"""
    enabled: bool = False
    browser_data_dir: str = ""  # Path to browser data, default: ~/.nanobot/browser_data/gying/
    headless: bool = True  # Run browser in headless mode
    check_schedule: str = "0 9 * * *"  # Cron expression for Scenario B update checks
    notify_channel: str = "feishu"  # Channel to push notifications to
    notify_to: str = ""  # User open_id or chat_id to push to
```

These would be added under a new `integrations` section in the config, or under `tools`.

### 5.2 Dependencies

**New Python dependencies**:
```
playwright>=1.40.0        # For gying.org SPA scraping
p115client>=0.0.5         # For 115.com API (primary choice, needs validation)
# OR py115>=0.1.0         # For 115.com API (fallback choice)
```

**System dependencies**:
```bash
playwright install chromium  # One-time browser binary install
```

---

## 6. Three Core Uncertainties & Spike Test Plan

Before any integration code is written, three fundamental uncertainties must be resolved through isolated spike tests. Each spike is a standalone script that validates one assumption. **No spike depends on another** — they can be executed in any order.

### 6.1 Uncertainty Map

| # | Uncertainty | Core Question | Spike Test | Exit Criteria |
|---|-----------|---------------|------------|---------------|
| U1 | **115 Library + QR Login** | Can we do QR login → save session → add magnet, entirely via API? | `tests/spike/spike_115_api.py` | Script completes full cycle: QR image → scan → session save → magnet add |
| U2 | **gying.org Scraping** | Can Playwright render gying.org SPA, handle login, extract movie data + listing page? | `tests/spike/spike_gying_scrape.py` | Script extracts title, rating, magnet link from detail page AND movie list from latest page |
| U3 | **Multi-turn Stateful Flow** | Can nanobot maintain context across a 5-turn conversation with tool state? | `tests/spike/spike_multi_turn.py` | Simulated conversation completes: search → select → login → download, with state preserved across turns |
| U4 | **Cron Push → Reply Flow** | Can cron push a message to Feishu and share session context with user reply? | `tests/spike/spike_cron_push.py` | Push arrives in Feishu, user reply is in same session, agent maintains context |

### 6.2 Architectural Context (from codebase analysis)

Before defining each spike, here's what the nanobot framework provides and what it lacks:

**What exists:**
- Session persistence: JSONL files, 50-message history loaded per turn (`session/manager.py`)
- Tools: Async `execute(**kwargs) -> str`, no timeout at framework level
- Subagent/spawn: `asyncio.create_task()` for background work, announces result via system message (`subagent.py`)
- Feishu channel: WebSocket-based, supports text + image + audio, has per-chat state dict (`_voice_reply_chats` pattern)

**What does NOT exist:**
- No tool-level state persistence API — tools must use file I/O manually
- No "pause and resume" — a tool cannot wait mid-execution for user input
- No card action callbacks — Feishu WebSocket doesn't receive button click events

**Implication for QR login flow:**
A tool CANNOT do "generate QR → send to user → wait for scan → return result" in a single `execute()` call. The flow must be split across multiple tool calls:
```
Turn 1: Tool generates QR, saves state file, returns QR image bytes
        → Agent sends QR to user via Feishu
Turn 2: User says "已扫码" or agent auto-checks after delay
        → Tool reads state file, polls 115 API, returns login result
```

OR use the spawn pattern for background polling (see Spike U3).

---

### 6.3 Spike U1: 115 API Library Validation

**File:** `tests/spike/spike_115_api.py`

**Purpose:** Determine which 115 library works, validate the full QR login → offline download cycle.

**Test sequence:**

```
Step 1: Library Import & Init
  - Try: import p115client (requires Python 3.12+)
  - Fallback: import py115 (Python 3.10+)
  - Last resort: mark Playwright as needed

Step 2: QR Code Generation
  - Call library's QR login API
  - Save QR image to tests/spike/output/qr_115.png
  - Print: "QR saved. Scan with 115 app within 120 seconds."

Step 3: Login Polling
  - Poll login status every 2 seconds, max 120 seconds
  - Handle states: waiting → scanned → confirmed → expired
  - On expiry: regenerate QR, restart polling
  - On success: save credentials to tests/spike/output/115_session.json

Step 4: Session Persistence
  - Reload session from file
  - Verify session is valid (call any authenticated API endpoint)

Step 5: Add Magnet Task
  - Use a test magnet link (a small, legal file)
  - Call offline download API
  - Verify task appears in task list
  - Clean up: delete the test task

Step 6: Session Expiry Handling
  - Intentionally corrupt session file
  - Verify library raises appropriate error
  - Verify re-login flow works
```

**Expected output:**
```
[PASS/FAIL] Library: p115client / py115
[PASS/FAIL] QR generation: saved to output/qr_115.png
[PASS/FAIL] Login polling: completed in Xs
[PASS/FAIL] Session save/load: 115_session.json valid
[PASS/FAIL] Add magnet: task created, id=xxx
[PASS/FAIL] Task cleanup: deleted
[PASS/FAIL] Session expiry detection: error raised correctly
```

**Key questions this spike answers:**
1. Which library actually works with current 115.com API?
2. What is the exact QR code lifecycle (image format, poll interval, expiry time)?
3. How are credentials serialized? Cookie dict? Token string? Opaque object?
4. What errors does the API return for: expired session, quota full, duplicate task?

---

### 6.4 Spike U2: gying.org Playwright Scraping

**File:** `tests/spike/spike_gying_scrape.py`

**Purpose:** Validate that Playwright can render, login to, and extract data from the gying.org SPA.

**Prerequisites:** A working gying.org account (username/password or other auth method — needs manual investigation first).

**Test sequence:**

```
Step 1: Browser Launch
  - Launch Playwright Chromium (headless=False for initial dev, headless=True for CI)
  - Apply stealth: playwright-stealth or manual navigator.webdriver removal
  - Set user_data_dir for cookie persistence

Step 2: Navigation & Anti-bot
  - Navigate to https://www.gying.org/
  - Wait for JS rendering to complete
  - Detect: did we get a login page, a Cloudflare challenge, or content?
  - Screenshot: tests/spike/output/gying_initial.png

Step 3: Login Flow (manual investigation needed)
  - [TBD] What auth mechanism does gying.org use?
  - Attempt login with provided credentials
  - Verify: authenticated state reached
  - Save cookies via context.storage_state()

Step 4: Search
  - Find the search input element (selector TBD)
  - Type a known movie name (e.g., "星际穿越")
  - Wait for results to load
  - Screenshot: tests/spike/output/gying_search.png
  - Extract: list of result items (title, URL, thumbnail)

Step 5: Movie Detail Page
  - Navigate to first search result URL
  - Wait for page to fully render
  - Extract and print:
    - Title (selector TBD)
    - Rating (selector TBD)
    - Genres
    - Actors
    - Synopsis
    - Poster image URL
  - Screenshot: tests/spike/output/gying_detail.png

Step 6: Download Links
  - Find the download section on the detail page
  - Extract ALL download links with their labels
  - Apply filter logic:
    - 4K + 中字: links containing ("4K" OR "2160P" OR "UHD") AND "中字"
    - 1080P + 中字: links containing ("1080P" OR "FHD") AND "中字"
  - Print: categorized link list with magnet URLs and file sizes
  - Screenshot: tests/spike/output/gying_links.png

Step 7: Document Selectors
  - Output all discovered CSS selectors to tests/spike/output/selectors.json
  - Format: { "search_input": "...", "result_items": "...", "title": "...", ... }

Step 8: Latest/Trending Listing Page (Scenario B prerequisite)
  - Navigate to homepage or "latest releases" page (URL TBD)
  - Wait for listing to render
  - Extract: list of movie items (title, URL, rating, thumbnail, date)
  - Screenshot: tests/spike/output/gying_latest.png
  - Verify: items have stable unique identifiers (URL or ID) for dedup
  - Document: listing page URL, listing item selectors, pagination mechanism
```

**Expected output:**
```
[PASS/FAIL] Browser launch + stealth
[PASS/FAIL] Page renders (not empty HTML)
[PASS/FAIL] Login: authenticated
[PASS/FAIL] Search: found N results for "星际穿越"
[PASS/FAIL] Detail: title="星际穿越", rating="9.4"
[PASS/FAIL] Links: found N total, M×4K中字, K×1080P中字
[PASS/FAIL] Latest listing: found N movies on latest page
[INFO] Selectors saved to output/selectors.json
[INFO] Screenshots saved to output/
```

**Key questions this spike answers:**
1. Does the SPA render under Playwright headless?
2. What is the actual login mechanism?
3. Are the CSS selectors stable (ID-based vs class-based vs positional)?
4. Does the site have anti-bot detection beyond Cloudflare?
5. What is the actual magnet link format and container structure?
6. **(Scenario B)** Does a "latest" or "trending" listing page exist? What's its URL and structure?

---

### 6.5 Spike U3: Multi-Turn Stateful Conversation Flow

**File:** `tests/spike/spike_multi_turn.py`

**Purpose:** Validate that nanobot's session + tool system can support a 5-turn stateful workflow without losing context. This is the integration-level spike.

**What this tests:**
- Can a tool store state (movie search results) and retrieve it in a later turn?
- Can the agent maintain a coherent conversation across search → select → login → download?
- Can the QR login flow work as a multi-turn interaction (not blocking)?

**Approach:** Write a minimal mock tool that simulates the film-download workflow using file-based state, and test it within the actual nanobot AgentLoop.

**Test sequence:**

```
Step 1: Setup
  - Instantiate AgentLoop with mock tools (no real gying/115)
  - MockGyingTool: returns hardcoded movie data
  - MockCloud115Tool:
    - action="check_session": reads state file, returns logged_in/not_logged_in
    - action="login": writes QR image path to state file, returns "请扫描二维码"
    - action="confirm_login": checks state file, returns success/timeout
    - action="add_magnet": returns "任务已添加"

Step 2: Simulate Turn 1 — User searches for movie
  - Input: "帮我找 星际穿越"
  - Expected: Agent calls MockGyingTool(action="search"), returns result list
  - Verify: Session saves the exchange

Step 3: Simulate Turn 2 — User selects movie
  - Input: "1"
  - Expected: Agent understands "1" means first result (from context history)
  - Expected: Agent calls MockGyingTool(action="detail") with correct URL
  - Verify: Context window contains Turn 1 history

Step 4: Simulate Turn 3 — User requests download
  - Input: "4K"
  - Expected: Agent calls MockGyingTool(action="links", resolution="4K")
  - Expected: Agent calls MockCloud115Tool(action="check_session")
  - If not logged in: Agent calls action="login", sends QR instructions
  - Verify: State file written with QR session data

Step 5: Simulate Turn 4 — User confirms QR scan
  - Input: "已扫码"
  - Expected: Agent calls MockCloud115Tool(action="confirm_login")
  - Expected: Returns "登录成功" and prompts for link selection

Step 6: Simulate Turn 5 — User selects link and downloads
  - Input: "1"
  - Expected: Agent calls MockCloud115Tool(action="add_magnet", magnet_url="...")
  - Expected: Returns confirmation message
```

**State persistence mechanism under test:**

```python
# State file: ~/.nanobot/workspace/film_download_state.json
{
  "search_results": [...],           # From Turn 1
  "selected_movie": {...},           # From Turn 2
  "download_links": [...],           # From Turn 3
  "qr_session": {"status": "..."},   # From Turn 3-4
  "last_updated": "..."
}
```

**Key question:** Does the agent correctly interpret short replies ("1", "4K", "已扫码") using session history context? Or does it need the skill prompt to explicitly instruct this behavior?

**Expected output:**
```
[PASS/FAIL] Turn 1: Search results returned, session saved
[PASS/FAIL] Turn 2: Agent connected "1" to search results via context
[PASS/FAIL] Turn 3: Links fetched, login check triggered, QR state saved
[PASS/FAIL] Turn 4: Login confirmed via state file
[PASS/FAIL] Turn 5: Download task added with correct magnet URL
[INFO] Total context tokens used across 5 turns: ~XXXX
[INFO] Session file size: XX messages
```

---

### 6.6 Spike U4: Cron Push → User Reply Flow (Scenario B)

**File:** `tests/spike/spike_cron_push.py`

**Purpose:** Validate the complete Scenario B path: cron triggers agent → agent pushes message to Feishu → user replies → agent continues with shared context.

**What this tests:**
- Does `CronService` correctly trigger `process_direct()` with `deliver=true`?
- Does the push message arrive in the user's Feishu chat?
- Does the user's reply share the same session as the push message?
- Can the agent connect the user's reply ("2") to the pushed movie list?

**Approach:** Use a simplified cron job that pushes a test message and verifies the reply round-trip.

**Test sequence:**

```
Step 1: Setup
  - Start nanobot gateway with Feishu channel enabled
  - Create a test cron job with deliver=true, targeting a specific Feishu chat

Step 2: Cron-triggered Push
  - Create cron job:
    name="test-push"
    schedule="in 10 seconds" (one-time, using ms interval)
    message="这是一条测试推送消息。包含以下选项：
             1. 选项A  2. 选项B  3. 选项C
             请回复序号选择"
    deliver=true
    channel="feishu"
    to="{test_chat_id}"
  - Wait for cron to fire
  - Verify: message appears in Feishu chat

Step 3: User Reply
  - User replies "2" in Feishu
  - Agent receives reply via normal message flow
  - Verify: agent's session history contains BOTH the push message and the reply
  - Verify: agent understands "2" refers to "选项B" from the push

Step 4: Session Key Verification
  - Check session file: should be under "feishu:{chat_id}"
  - Verify: push message and user reply are in the SAME session
  - Print session contents for manual inspection

Step 5: Context Continuity
  - Send follow-up message: "选了什么？"
  - Verify: agent recalls the previous selection (from session history)
```

**Expected output:**
```
[PASS/FAIL] Cron job created and scheduled
[PASS/FAIL] Push message delivered to Feishu chat
[PASS/FAIL] User reply received by agent
[PASS/FAIL] Session key matches: feishu:{chat_id}
[PASS/FAIL] Agent correctly interpreted "2" as 选项B
[PASS/FAIL] Follow-up context preserved
[INFO] Session file: {path}
```

**Key questions this spike answers:**
1. Does `deliver=true` actually send the message to Feishu? (or just return to CLI?)
2. Is the cron job's session key compatible with the user's reply session key?
3. Does the agent's process_direct response get saved to the session before the user replies?
4. What latency is there between cron fire and Feishu delivery?

**Note:** This spike requires a running Feishu channel and a real Feishu test account. It cannot be fully mocked.

---

### 6.7 Spike Execution Order & Dependencies

```
U1 (115 API)  ──────────────────→  Can run independently
U2 (gying scrape) ─────────────→  Can run independently
U3 (multi-turn) ───────────────→  Can run independently (uses mocks)
                                    BUT: results from U1/U2 improve mock fidelity
U4 (cron push) ────────────────→  Requires running Feishu channel
                                    Can run independently from U1/U2

Recommended order:
  1. U1 first (fastest to validate, no browser needed)
  2. U2 second (needs manual DOM investigation)
  3. U4 third (validates cron→Feishu pipeline, needs real Feishu)
  4. U3 last (benefits from knowing exact return formats from U1/U2/U4)
```

### 6.8 Spike Exit Criteria → Implementation Gate

| Spike | Must Pass | Can Proceed Without |
|-------|-----------|-------------------|
| U1 | At least one library (p115client/py115) completes QR login + add magnet | Open API support, task list/delete |
| U2 | Playwright renders page, extracts at least title + one magnet link + listing page works | Poster images, actor list, genre tags |
| U3 | Agent maintains context across 5 turns, tool state persists | Optimal prompt engineering, edge cases |
| U4 | Cron push arrives in Feishu, user reply shares session context | Latency optimization, error recovery |

**If a spike fails:**
- U1 all libraries fail → fall back to Playwright for 115 (add to U2 scope)
- U2 Playwright blocked → investigate API reverse-engineering or find alternative movie site
- U3 context lost → need to implement explicit state management (add middleware or custom session handler)
- U4 cron push fails → investigate `deliver=true` behavior, may need to call message tool explicitly instead

---

## 7. Implementation Plan (Post-Spike)

Implementation only begins after all four spikes pass their exit criteria.

### Phase 1: Core Tools (Scenario A foundation)

| Task | File | Description | Depends On |
|------|------|-------------|------------|
| **1.1** Implement Cloud115Tool | `nanobot/agent/tools/cloud115.py` | Wrap validated library from Spike U1 | U1 result |
| **1.2** Implement GyingScraperTool | `nanobot/agent/tools/gying.py` | Wrap Playwright logic from Spike U2 (search + detail + links) | U2 result |
| **1.3** Implement tool state persistence | `nanobot/agent/tools/state.py` (new) | Shared JSON state file helper for multi-turn workflows | U3 result |
| **1.4** Register tools | `nanobot/agent/tools/registry.py` | Conditional registration based on config | 1.1, 1.2 |
| **1.5** Add config schema | `nanobot/config/schema.py` | Cloud115Config, GyingConfig | None |
| **1.6** Unit tests (mocked) | `tests/test_cloud115.py`, `tests/test_gying.py` | Validate tool interfaces with mocked backends | 1.1, 1.2 |

### Phase 2: Skill & Multi-Turn Integration (Scenario A complete)

| Task | File | Description |
|------|------|-------------|
| **2.1** Create film-download skill | `nanobot/skills/film-download/SKILL.md` | Orchestration prompt covering both Scenario A and B |
| **2.2** QR login multi-turn flow | `nanobot/agent/tools/cloud115.py` | Split login into: generate_qr → check_scan → save_session |
| **2.3** Integration test (manual) | `tests/test_film_workflow.py` | Real Feishu conversation test for Scenario A |

### Phase 3: Scheduled Push (Scenario B)

| Task | File | Description | Depends On |
|------|------|-------------|------------|
| **3.1** Implement GyingUpdatesTool | `nanobot/agent/tools/gying.py` | Browse latest page, compare against seen_movies.json, return new entries | U2, U4 results |
| **3.2** Implement seen_movies.json management | `nanobot/agent/tools/gying.py` | Dedup logic: read/write seen list, mark notified, periodic cleanup | 3.1 |
| **3.3** Configure cron job | Config or CLI setup | Create daily check job with deliver=true targeting Feishu | U4 result |
| **3.4** Scenario B integration test | `tests/test_push_workflow.py` | Cron fires → agent scrapes → push to Feishu → user replies → download | 3.1, 3.3 |

### Phase 4: Polish

| Task | Description |
|------|-------------|
| **4.1** Poster image in Feishu messages | Download poster from gying, send as image |
| **4.2** Session auto-recovery | Detect 115 expiry, auto-trigger re-login |
| **4.3** Error UX | User-friendly Chinese error messages for all failure modes |
| **4.4** seen_movies.json cleanup | Auto-remove entries older than 90 days |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| gying.org DOM structure changes | High | Tool breaks | Centralize selectors in config. Log raw HTML on failure. |
| gying.org closed registration | Medium | Cannot test | Need existing account. Manual investigation required. |
| Both 115 libraries fail | Low | Must use Playwright for 115 | Spike U1 validates this early. Playwright fallback designed. |
| 115.com blocks API login | Medium | QR login fails | Playwright fallback. Test with different `app` parameters. |
| Multi-turn context loss | Medium | Broken UX | Spike U3 validates. File-based state as backup to LLM context. |
| QR code expires before user scans | High | Login fails | Auto-detect expiry, regenerate, re-send. Extend timeout to 180s. |
| Playwright detected by gying.org | Low | Scraping blocked | `playwright-stealth`, custom User-Agent, real browser profile. |
| Cron push session mismatch | Medium | User reply starts new session | Spike U4 validates. Ensure session_key format matches. |
| Daily scrape triggers rate limit | Medium | Temporary ban | Random delay before scrape. Respect robots.txt. Cache aggressively. |

---

## 9. Differences from Original README.md Proposal

| Aspect | README.md (Original) | DESIGN.md (Revised) |
|--------|----------------------|----------------------|
| User scenarios | Implicit push + pull | Explicit Scenario A (pull) + Scenario B (push) with separate flows |
| 115.com approach | Playwright browser automation | API library (p115client/py115), validated by spike test |
| Feishu interaction | Interactive card callbacks | Text-based commands (no webhook server needed) |
| Scheduled updates | Described but not designed | CronService with `deliver=true`, seen_movies.json dedup, GyingUpdatesTool |
| CSS selectors | Speculative (generic assumptions) | TBD — discovered during Spike U2 |
| QR login flow | Single blocking operation | Multi-turn: generate QR (Turn N) → confirm scan (Turn N+1) |
| State management | Browser Context Protocol | File-based JSON state + LLM session history |
| Development approach | Build 4 modules then integrate | 4 spike tests first → implementation only after validation |
| Validation strategy | Assumed everything works | Each uncertainty has explicit test with pass/fail criteria |

---

## 10. Open Questions

1. **gying.org account**: Do we have a working account? Is registration open?
2. **gying.org login mechanism**: Username/password? Social login? Invite-only?
3. **gying.org listing page**: Is there a dedicated "latest releases" or "new additions" page? What's the URL?
4. **Python version**: Is Python 3.12+ acceptable? (Required for p115client)
5. **115 credentials format**: Cookie-based? Open API tokens? Both?
6. **Test magnet link**: What's a safe, small magnet link for testing 115 offline download?
7. **Concurrent users**: Will multiple Feishu users use this simultaneously? (Affects browser instance management and cron job per-user setup)
8. **Push frequency**: Daily at 09:00? Or configurable? Should the user be able to say "每天帮我检查新片" to set up the cron?
9. **Content categories**: Should Scenario B check all categories (latest, 4K, trending) or just one? User-configurable?
