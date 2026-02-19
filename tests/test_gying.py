"""Tests for GyingScraperTool."""

import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_gying_tool_interface():
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    assert tool.name == "gying_search"
    assert "action" in tool.parameters["properties"]
    actions = set(tool.parameters["properties"]["action"]["enum"])
    assert actions == {"search", "detail", "links"}


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
