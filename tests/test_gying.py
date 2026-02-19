"""Tests for GyingScraperTool."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_gying_tool_interface():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    assert tool.name == "gying_search"
    assert "action" in tool.parameters["properties"]
    actions = set(tool.parameters["properties"]["action"]["enum"])
    assert actions == {"search", "detail", "links", "select", "select_link"}


@pytest.mark.asyncio
async def test_gying_search_returns_json():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    with patch.object(tool, "_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"title": "星际穿越 Interstellar (2014)", "url": "/mv/ZKpM", "rating": "豆瓣 9.4"}
        ]
        result = await tool.execute(action="search", query="星际穿越")
        data = json.loads(result)
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["title"] == "星际穿越 Interstellar (2014)"


@pytest.mark.asyncio
async def test_gying_search_requires_query():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    result = await tool.execute(action="search")
    assert "query" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_gying_detail_returns_movie_info():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    with patch.object(tool, "_detail", new_callable=AsyncMock) as mock_detail:
        mock_detail.return_value = {
            "title": "星际穿越",
            "year": "(2014)",
            "douban_rating": "9.4",
            "genres": ["科幻", "冒险", "剧情"],
            "synopsis": "一队探险家...",
        }
        result = await tool.execute(action="detail", url="/mv/ZKpM")
        data = json.loads(result)
        assert data["title"] == "星际穿越"
        assert "genres" in data


@pytest.mark.asyncio
async def test_gying_detail_requires_url():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    result = await tool.execute(action="detail")
    assert "url" in result.lower() or "error" in result.lower()


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


@pytest.mark.asyncio
async def test_gying_links_no_matching_tabs():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    with patch.object(tool, "_links", new_callable=AsyncMock) as mock_links:
        mock_links.return_value = []  # No matching tabs
        result = await tool.execute(action="links", url="/mv/ZKpM", quality="4K")
        data = json.loads(result)
        assert data["links"] == []


def _write_cache_file(data: dict) -> str:
    """Write seen_movies data to a temp file."""
    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False)
        return f.name


@pytest.mark.asyncio
async def test_gying_search_updates_cache():
    """Search action writes results to seen_movies.json cache."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({"movies": {}, "last_check": ""})
    tool = GyingScraperTool(seen_file=seen_path)
    with patch.object(tool, "_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"title": "星际穿越", "url": "/mv/ZKpM", "rating": "9.4"},
            {"title": "星际迷航", "url": "/mv/ABcD", "rating": "8.1"},
        ]
        await tool.execute(action="search", query="星际穿越")

    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    # Movies written to global registry
    assert "/mv/ZKpM" in saved["movies"]
    assert saved["movies"]["/mv/ZKpM"]["title"] == "星际穿越"
    assert saved["movies"]["/mv/ZKpM"]["rating"] == "9.4"
    # last_query written with ordered URLs
    assert saved["last_query"]["urls"] == ["/mv/ZKpM", "/mv/ABcD"]

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_select_resolves_index():
    """Select action returns movie info from last_query cache."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({
        "movies": {
            "/mv/AAA": {"title": "Movie A", "rating": "8.0", "tag": "4K", "first_seen": "2026-02-19", "notified": False},
            "/mv/BBB": {"title": "Movie B", "rating": "7.5", "tag": "1080P", "first_seen": "2026-02-19", "notified": False},
            "/mv/CCC": {"title": "Movie C", "rating": "9.0", "tag": "4K", "first_seen": "2026-02-19", "notified": False},
        },
        "last_query": {
            "timestamp": "2026-02-19T19:00:00",
            "urls": ["/mv/AAA", "/mv/BBB", "/mv/CCC"],
        },
        "last_check": "",
    })
    tool = GyingScraperTool(seen_file=seen_path)

    # Select index 2 → should return Movie B
    result = await tool.execute(action="select", index=2)
    data = json.loads(result)
    assert data["url"] == "/mv/BBB"
    assert data["title"] == "Movie B"
    assert data["rating"] == "7.5"

    # Select index 3 → should return Movie C
    result = await tool.execute(action="select", index=3)
    data = json.loads(result)
    assert data["url"] == "/mv/CCC"
    assert data["title"] == "Movie C"

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_select_invalid_index():
    """Select action returns error for out-of-range index."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({
        "movies": {"/mv/AAA": {"title": "A", "rating": "", "tag": "", "first_seen": "2026-02-19", "notified": False}},
        "last_query": {"timestamp": "2026-02-19T19:00:00", "urls": ["/mv/AAA"]},
        "last_check": "",
    })
    tool = GyingScraperTool(seen_file=seen_path)

    result = await tool.execute(action="select", index=5)
    data = json.loads(result)
    assert "error" in data
    assert "1-1" in data["error"]

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_select_no_cache():
    """Select action returns error when no cache file exists."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool(seen_file="/tmp/nonexistent_cache_12345.json")
    result = await tool.execute(action="select", index=1)
    data = json.loads(result)
    assert "error" in data


@pytest.mark.asyncio
async def test_gying_select_no_last_query():
    """Select action returns error when cache has no last_query."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({"movies": {}, "last_check": ""})
    tool = GyingScraperTool(seen_file=seen_path)
    result = await tool.execute(action="select", index=1)
    data = json.loads(result)
    assert "error" in data

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_links_updates_cache():
    """Links action writes results to seen_movies.json last_links cache."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({"movies": {}, "last_check": ""})
    tool = GyingScraperTool(seen_file=seen_path)
    mock_links = [
        {"name": "Movie.4K.中字.mkv", "magnet": "magnet:?xt=urn:btih:aaa", "size": "14GB", "seeds": "30", "quality_tab": "中字4K"},
        {"name": "Movie.1080p.中字.mkv", "magnet": "magnet:?xt=urn:btih:bbb", "size": "3GB", "seeds": "100", "quality_tab": "中字1080P"},
    ]
    with patch.object(tool, "_links", new_callable=AsyncMock) as mock:
        mock.return_value = mock_links
        await tool.execute(action="links", url="/mv/ZKpM")

    saved = json.loads(Path(seen_path).read_text(encoding="utf-8"))
    assert "last_links" in saved
    assert len(saved["last_links"]["links"]) == 2
    assert saved["last_links"]["links"][0]["magnet"] == "magnet:?xt=urn:btih:aaa"
    assert saved["last_links"]["links"][1]["magnet"] == "magnet:?xt=urn:btih:bbb"

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_select_link_resolves_index():
    """Select_link action returns link info from last_links cache."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({
        "movies": {},
        "last_check": "",
        "last_links": {
            "timestamp": "2026-02-19T20:00:00",
            "links": [
                {"name": "Movie.4K.中字.mkv", "magnet": "magnet:?xt=urn:btih:aaa", "size": "14GB", "seeds": "30", "quality_tab": "中字4K"},
                {"name": "Movie.1080p.中字.mkv", "magnet": "magnet:?xt=urn:btih:bbb", "size": "3GB", "seeds": "100", "quality_tab": "中字1080P"},
                {"name": "Movie[简繁英].1080p.mkv", "magnet": "magnet:?xt=urn:btih:ccc", "size": "5.5GB", "seeds": "36", "quality_tab": "中字1080P"},
            ],
        },
    })
    tool = GyingScraperTool(seen_file=seen_path)

    # Select link 2 → should return 1080p link
    result = await tool.execute(action="select_link", index=2)
    data = json.loads(result)
    assert data["magnet"] == "magnet:?xt=urn:btih:bbb"
    assert data["name"] == "Movie.1080p.中字.mkv"
    assert data["quality_tab"] == "中字1080P"

    # Select link 1 → should return 4K link
    result = await tool.execute(action="select_link", index=1)
    data = json.loads(result)
    assert data["magnet"] == "magnet:?xt=urn:btih:aaa"

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_select_link_invalid_index():
    """Select_link action returns error for out-of-range index."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({
        "movies": {},
        "last_check": "",
        "last_links": {
            "timestamp": "2026-02-19T20:00:00",
            "links": [
                {"name": "Movie.mkv", "magnet": "magnet:?xt=urn:btih:aaa", "size": "14GB", "seeds": "30", "quality_tab": "中字4K"},
            ],
        },
    })
    tool = GyingScraperTool(seen_file=seen_path)

    result = await tool.execute(action="select_link", index=5)
    data = json.loads(result)
    assert "error" in data
    assert "1-1" in data["error"]

    Path(seen_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gying_select_link_no_cache():
    """Select_link action returns error when no last_links in cache."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    seen_path = _write_cache_file({"movies": {}, "last_check": ""})
    tool = GyingScraperTool(seen_file=seen_path)
    result = await tool.execute(action="select_link", index=1)
    data = json.loads(result)
    assert "error" in data

    Path(seen_path).unlink(missing_ok=True)
