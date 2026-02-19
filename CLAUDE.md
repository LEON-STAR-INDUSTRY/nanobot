# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**nanobot** is an ultra-lightweight (~4,000 LOC) personal AI assistant framework written in Python 3.11+. It provides an event-driven async agent loop with multi-channel chat platform support (Telegram, Discord, Feishu, WhatsApp).

## Build & Development Commands

```bash
# Install (development)
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
pytest tests/test_tool_validation.py -v   # single test file

# Lint & format
ruff check nanobot/ tests/
ruff check --fix nanobot/ tests/
ruff format nanobot/ tests/

# CLI commands
nanobot onboard                    # Initialize config & workspace
nanobot agent -m "message"         # Single message
nanobot agent                      # Interactive mode
nanobot gateway                    # Start multi-channel gateway

# Docker
docker build -t nanobot .
docker run -v ~/.nanobot:/root/.nanobot nanobot gateway
```

## Architecture

### Message Flow

```
Chat Platforms (Telegram/Discord/Feishu/WhatsApp)
    ↕ BaseChannel implementations
MessageBus (async queue: InboundMessage / OutboundMessage)
    ↕
AgentLoop (core reasoning engine)
    ├── ContextBuilder (prompt + history + memory + skills)
    ├── LLMProvider (LiteLLM, multi-provider)
    └── ToolRegistry → Tool implementations
```

### Key Modules

- **`nanobot/agent/loop.py`** - `AgentLoop`: Core reasoning loop. Receives messages from bus, builds context, calls LLM, executes tool calls, sends responses. Max iterations configurable (default 20).
- **`nanobot/agent/context.py`** - `ContextBuilder`: Assembles prompt from conversation history, memory, and skills.
- **`nanobot/agent/tools/`** - Tool implementations. All inherit from `Tool` ABC (`base.py`). Registered in `ToolRegistry` (`registry.py`). Built-in: filesystem, shell, web, message, spawn, cron.
- **`nanobot/agent/memory.py`** - `MemoryStore`: Daily notes (`memory/YYYY-MM-DD.md`) + long-term (`MEMORY.md`).
- **`nanobot/agent/skills.py`** - `SkillsLoader`: Loads markdown-based skills from `nanobot/skills/` (builtin) and `{workspace}/skills/` (custom).
- **`nanobot/agent/subagent.py`** - `SubagentManager`: Background task execution via spawn tool.
- **`nanobot/channels/`** - Chat platform integrations. All inherit from `BaseChannel` ABC (`base.py`). Managed by `ChannelManager` (`manager.py`).
- **`nanobot/providers/`** - LLM integration via LiteLLM. `LLMProvider` ABC in `base.py`, implementation in `litellm_provider.py`. Voice transcription via Groq Whisper in `transcription.py`.
- **`nanobot/bus/`** - Async message bus. `InboundMessage`/`OutboundMessage` dataclasses in `events.py`, `MessageBus` queue in `queue.py`.
- **`nanobot/config/`** - Pydantic v2 config. Schema in `schema.py`, loading/saving in `loader.py`. Config at `~/.nanobot/config.json` with automatic camelCase (JSON) ↔ snake_case (Python) conversion. Environment variables via `NANOBOT_` prefix with `__` nesting.
- **`nanobot/cron/`** - Job scheduling with croniter expressions.
- **`nanobot/heartbeat/`** - Periodic agent wake-up service.
- **`nanobot/session/manager.py`** - JSONL-based conversation persistence per channel:chat_id.
- **`nanobot/cli/commands.py`** - Typer CLI entry point.
- **`bridge/`** - Node.js WhatsApp bridge using Baileys library, communicates with Python via WebSocket.

## Conventions

- **Async-first**: All I/O is async (asyncio). Tools use `async def execute()`.
- **Logging**: Loguru (`from loguru import logger`), not stdlib logging.
- **Ruff config**: Line length 100, Python 3.11 target, rules: E/F/I/N/W (E501 ignored).
- **Tool interface**: Properties `name`, `description`, `parameters` (JSON Schema), method `async execute(**kwargs) -> str`. Errors returned as strings, not raised.
- **Skill format**: `SKILL.md` markdown files with optional YAML frontmatter. Located in `nanobot/skills/{name}/SKILL.md` or `{workspace}/skills/{name}/SKILL.md`.
- **Channel interface**: `BaseChannel` ABC with `start()`, `stop()`, `send()` methods. Constructor takes `(config, bus)`.
- **Config keys**: JSON files use camelCase, Python code uses snake_case. Auto-converted by loader.
- **Shell safety**: `ExecTool` blocks dangerous patterns (rm -rf /, mkfs, fork bombs). `restrict_to_workspace` flag sandboxes file operations.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| CLI | Typer |
| LLM | LiteLLM (multi-provider) |
| Config/Validation | Pydantic v2 |
| HTTP | httpx (with SOCKS proxy) |
| Telegram | python-telegram-bot |
| Feishu | lark-oapi (WebSocket) |
| Discord | Custom WebSocket gateway |
| WhatsApp | Node.js Baileys bridge |
| Web parsing | readability-lxml |
| Scheduling | croniter |
| Testing | pytest + pytest-asyncio (auto mode) |
| Lint/Format | Ruff |
| Build | Hatchling |
