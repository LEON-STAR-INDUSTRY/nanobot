# DOCUMENT METADATA
title: Film Download Skill - Summary
filename: 09-film_download_skill.md
status: Approved
version: 1.1.0
owner: AI Assistant
last_updated: 2026-02-19
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-15 | Claude | Initial creation       |
| 1.1.0   | 2026-02-19 | Claude | Added anti-fabrication rules, manual/cron distinction, ordering constraint |

## Purpose & Scope
> Summary of Task 9: Create the Film Download orchestration skill for Scenario A and B.

---

## Implementation Summary

Created `nanobot/skills/film-download/SKILL.md`, a markdown-based orchestration skill that teaches the agent the complete film download workflow. The skill uses `always_load: true` frontmatter to ensure it's always available in the agent's context.

The skill covers:
1. **Scenario A (Pull)**: User-initiated search flow — search → detail → links → login → download
2. **Scenario B (Push/Manual)**: Supports both cron-triggered and user-initiated latest movie queries
   - User manual query (`source="manual"`): returns all listings without seen filtering
   - Cron trigger (`source="cron"`): returns only new unseen items
3. **Anti-fabrication rules**: Strict instructions prohibiting LLM from fabricating download links or movie lists
4. **Ordering constraint**: Results must be displayed in original tool-returned order, no reordering allowed
5. **Cron setup**: Instructions for creating daily check jobs when user requests it
6. **Error handling**: Chinese error messages for all failure modes
7. **Interaction conventions**: Number-based selection, resolution preferences, short reply interpretation

The skill references three tools: `gying_search`, `gying_check_updates`, and `cloud115`.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nanobot/skills/film-download/SKILL.md` | Created | Orchestration skill with Scenario A/B workflows |

## Test Results

Verified skill loads correctly via `SkillsLoader.load_skill('film-download')` — returns non-empty content.

## Issues & Notes

- The skill uses `always_load: true` which means it will be included in every agent conversation context, adding to token usage. This is intentional since the film download feature should always be available.
- `gying_check_updates` tool referenced in the skill does not exist yet — it will be implemented in Task 12.
- The cron setup section references the existing `cron` tool for creating scheduled jobs.
