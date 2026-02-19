"""Tests for GyingUpdatesTool."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


def _write_seen_file(data: dict) -> str:
    """Write seen_movies data to a temp file with utf-8 encoding."""
    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False)
        return f.name


@pytest.mark.asyncio
async def test_gying_updates_tool_interface():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    tool = GyingUpdatesTool()
    assert tool.name == "gying_check_updates"
    assert "source" in tool.parameters["properties"]


@pytest.mark.asyncio
async def test_gying_updates_returns_new_movies():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({"movies": {}, "last_check": ""})
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "沙丘3 (2026)", "url": "/mv/AAA", "rating": "8.7", "tag": "4K"},
        {"title": "黑暗骑士 (2026)", "url": "/mv/BBB", "rating": "9.1", "tag": "1080P"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        result = await tool.execute(source="cron")
        data = json.loads(result)

        assert data["new_count"] == 2
        assert len(data["new_movies"]) == 2
        assert data["new_movies"][0]["title"] == "沙丘3 (2026)"

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_filters_seen():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({
        "movies": {
            "/mv/AAA": {"title": "沙丘3", "first_seen": "2026-02-14", "notified": True},
        },
        "last_check": "2026-02-14T09:00:00",
    })
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "沙丘3 (2026)", "url": "/mv/AAA", "rating": "8.7", "tag": "4K"},
        {"title": "黑暗骑士 (2026)", "url": "/mv/BBB", "rating": "9.1", "tag": "1080P"},
        {"title": "流浪地球3 (2026)", "url": "/mv/CCC", "rating": "8.3", "tag": "4K"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        result = await tool.execute(source="cron")
        data = json.loads(result)

        assert data["total_checked"] == 3
        assert data["previously_seen"] == 1
        assert data["new_count"] == 2
        urls = [m["url"] for m in data["new_movies"]]
        assert "/mv/AAA" not in urls
        assert "/mv/BBB" in urls
        assert "/mv/CCC" in urls

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_saves_seen():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({"movies": {}, "last_check": ""})
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "新片 (2026)", "url": "/mv/NEW", "rating": "7.5", "tag": "1080P"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        await tool.execute(source="cron")

    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    assert "/mv/NEW" in saved["movies"]
    assert saved["movies"]["/mv/NEW"]["title"] == "新片 (2026)"
    assert saved["movies"]["/mv/NEW"]["rating"] == "7.5"
    assert saved["movies"]["/mv/NEW"]["tag"] == "1080P"
    assert saved["last_check"] != ""

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_no_new_movies():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({
        "movies": {
            "/mv/AAA": {"title": "老片", "first_seen": "2026-02-01", "notified": True},
        },
        "last_check": "2026-02-14T09:00:00",
    })
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "老片 (2024)", "url": "/mv/AAA", "rating": "8.0", "tag": "4K"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        result = await tool.execute(source="cron")
        data = json.loads(result)

        assert data["new_count"] == 0
        assert len(data["new_movies"]) == 0

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_max_results():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({"movies": {}, "last_check": ""})
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": f"Movie{i}", "url": f"/mv/{i}", "rating": "7.0", "tag": "1080P"}
        for i in range(20)
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        result = await tool.execute(source="cron", max_results=5)
        data = json.loads(result)

        assert data["new_count"] == 5
        assert len(data["new_movies"]) == 5

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_cleanup_removes_old():
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({
        "movies": {
            "/mv/OLD": {
                "title": "Old Movie",
                "first_seen": "2025-01-01",
                "notified": True,
            },
            "/mv/RECENT": {
                "title": "Recent Movie",
                "first_seen": "2026-02-10",
                "notified": True,
            },
        },
        "last_check": "2026-02-14T09:00:00",
    })

    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "Brand New (2026)", "url": "/mv/NEW", "rating": "8.0", "tag": "4K"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        await tool.execute(source="cron")

    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    # OLD (>90 days) should be removed
    assert "/mv/OLD" not in saved["movies"]
    # RECENT (<90 days) should be preserved
    assert "/mv/RECENT" in saved["movies"]
    # NEW should be added
    assert "/mv/NEW" in saved["movies"]

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_manual_returns_all():
    """source='manual' returns all listings and writes to global registry + last_query."""
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({
        "movies": {
            "/mv/AAA": {"title": "沙丘3", "rating": "8.7", "tag": "4K", "first_seen": "2026-02-14", "notified": True},
        },
        "last_check": "2026-02-14T09:00:00",
    })
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "沙丘3 (2026)", "url": "/mv/AAA", "rating": "8.7", "tag": "4K"},
        {"title": "黑暗骑士 (2026)", "url": "/mv/BBB", "rating": "9.1", "tag": "1080P"},
        {"title": "流浪地球3 (2026)", "url": "/mv/CCC", "rating": "8.3", "tag": "4K"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        result = await tool.execute(source="manual")
        data = json.loads(result)

        # Manual returns all movies (including seen ones), uses "movies" key
        assert "movies" in data
        assert data["count"] == 3
        assert data["total"] == 3
        urls = [m["url"] for m in data["movies"]]
        assert "/mv/AAA" in urls  # Not filtered out
        assert "/mv/BBB" in urls
        assert "/mv/CCC" in urls
        # Order preserved from listing
        assert data["movies"][0]["title"] == "沙丘3 (2026)"
        assert data["movies"][1]["title"] == "黑暗骑士 (2026)"
        assert data["movies"][2]["title"] == "流浪地球3 (2026)"

    # Seen file SHOULD be updated (global registry + last_query)
    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    # All movies written to global registry
    assert "/mv/AAA" in saved["movies"]
    assert "/mv/BBB" in saved["movies"]
    assert "/mv/CCC" in saved["movies"]
    # Existing entry preserves notified=True and first_seen
    assert saved["movies"]["/mv/AAA"]["notified"] is True
    assert saved["movies"]["/mv/AAA"]["first_seen"] == "2026-02-14"
    # New entries have notified=False
    assert saved["movies"]["/mv/BBB"]["notified"] is False
    assert saved["movies"]["/mv/CCC"]["notified"] is False
    # Rating and tag persisted
    assert saved["movies"]["/mv/BBB"]["rating"] == "9.1"
    assert saved["movies"]["/mv/BBB"]["tag"] == "1080P"
    # last_query written with ordered URLs
    assert "last_query" in saved
    assert saved["last_query"]["urls"] == ["/mv/AAA", "/mv/BBB", "/mv/CCC"]

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_manual_preserves_existing():
    """Manual mode doesn't overwrite first_seen or notified on existing entries."""
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    seen_path = _write_seen_file({
        "movies": {
            "/mv/AAA": {"title": "Old Title", "rating": "7.0", "tag": "4K", "first_seen": "2026-01-01", "notified": True},
        },
        "last_check": "2026-02-14T09:00:00",
    })
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "Updated Title (2026)", "url": "/mv/AAA", "rating": "8.5", "tag": "4K"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        await tool.execute(source="manual")

    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    entry = saved["movies"]["/mv/AAA"]
    # Title and rating updated to latest
    assert entry["title"] == "Updated Title (2026)"
    assert entry["rating"] == "8.5"
    # first_seen and notified preserved from original
    assert entry["first_seen"] == "2026-01-01"
    assert entry["notified"] is True

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_updates_cleanup_caps_at_100():
    """Cleanup caps movies at 100 entries, removing oldest first."""
    from nanobot.agent.tools.integrations.gying.tool import GyingUpdatesTool

    # Create 105 existing entries with sequential dates
    existing_movies = {}
    for i in range(105):
        day = f"2026-01-{(i % 28) + 1:02d}"
        existing_movies[f"/mv/{i:04d}"] = {
            "title": f"Movie {i}",
            "rating": "7.0",
            "tag": "1080P",
            "first_seen": day,
            "notified": True,
        }

    seen_path = _write_seen_file({"movies": existing_movies, "last_check": ""})
    tool = GyingUpdatesTool(seen_file=seen_path)
    mock_listing = [
        {"title": "Brand New (2026)", "url": "/mv/NEW1", "rating": "8.0", "tag": "4K"},
    ]
    with patch.object(tool, "_scrape_listing", new_callable=AsyncMock) as mock:
        mock.return_value = mock_listing
        await tool.execute(source="cron")

    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    # Should be capped at 100 (105 existing - removed oldest + 1 new)
    assert len(saved["movies"]) <= 100
    # New entry should be present
    assert "/mv/NEW1" in saved["movies"]

    Path(seen_path).unlink(missing_ok=True)
