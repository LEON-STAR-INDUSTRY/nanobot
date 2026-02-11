# DOCUMENT METADATA
title: Spike U2 — gying.org Playwright Scraping Results
filename: 02-spike_u2_gying_scrape.md
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
> Summary of Spike U2: Validate that Playwright can render the gying.org SPA, handle authentication, and extract movie data.

---

## Implementation Summary

### Spike Script
- `tests/spike/spike_gying_scrape.py`

### Browser Configuration
- Chromium with persistent `user_data_dir` for cookie retention
- `playwright-stealth` for anti-detection (optional fallback: manual `navigator.webdriver` removal)
- Headed mode recommended for initial spike (manual login may be required)
- Locale: `zh-CN`, Viewport: 1280x800

### Test Scenarios
1. **Browser launch + stealth** — Verify Chromium launches without detection
2. **Page render** — Verify gying.org loads (not empty HTML)
3. **Auth investigation** — Detect login mechanism and authenticate
4. **Search** — Search "星际穿越", extract result list
5. **Detail page** — Extract title, rating, genres, synopsis
6. **Download links** — Extract magnet links, filter 4K+中字 and 1080P+中字
7. **Latest listing** — Scrape homepage movie listing for Scenario B

### Selectors
- Discovered selectors saved to `tests/spike/output/selectors.json`
- Storage state saved to `tests/spike/output/gying_storage_state.json`
- Screenshots saved to `tests/spike/output/screenshots/`

## Test Results

> **Status: PENDING** — Run `python tests/spike/spike_gying_scrape.py` manually in headed mode.

## Issues & Notes
- gying.org may use Cloudflare protection — spike includes wait/retry logic
- Login mechanism unknown until first run — spike includes manual 30s login window
- Selectors may need updating if site changes
- Persistent browser data ensures cookies survive across runs
