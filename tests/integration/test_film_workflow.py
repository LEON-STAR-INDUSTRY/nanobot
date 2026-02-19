"""Integration test for Scenario A: User-initiated film search and download.

This test validates the complete workflow using mocked tool backends:
  Turn 1: Search for movie → returns results
  Turn 2: Select movie → returns detail
  Turn 3: Request download links → returns links + login check
  Turn 4: Login via QR → confirms login
  Turn 5: Select link → adds magnet download

Run: pytest tests/integration/test_film_workflow.py -v
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

import pytest  # noqa: F401

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_SEARCH_RESULTS = [
    {"title": "星际穿越 Interstellar (2014)", "url": "/mv/ZKpM", "rating": "豆瓣 9.4"},
    {"title": "星际迷航 Star Trek (2009)", "url": "/mv/ABcD", "rating": "豆瓣 8.1"},
]

MOCK_DETAIL = {
    "title": "星际穿越",
    "year": "(2014)",
    "douban_rating": "9.4",
    "imdb_rating": "8.7",
    "genres": ["科幻", "冒险", "剧情"],
    "synopsis": "在不远的未来，随着地球自然环境的恶化...",
    "poster": "https://example.com/poster.jpg",
    "url": "/mv/ZKpM",
}

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_returns_results():
    """Turn 1: Search for a movie."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    with patch.object(tool, "_search", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_SEARCH_RESULTS
        result = await tool.execute(action="search", query="星际穿越")
        data = json.loads(result)

        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["title"] == "星际穿越 Interstellar (2014)"
        assert data["results"][0]["url"] == "/mv/ZKpM"


@pytest.mark.asyncio
async def test_detail_returns_movie_info():
    """Turn 2: Get detail for selected movie."""
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    tool = GyingScraperTool()
    url = MOCK_SEARCH_RESULTS[0]["url"]
    with patch.object(tool, "_detail", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_DETAIL
        result = await tool.execute(action="detail", url=url)
        data = json.loads(result)

        assert data["title"] == "星际穿越"
        assert data["douban_rating"] == "9.4"
        assert "科幻" in data["genres"]


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


@pytest.mark.asyncio
async def test_check_session_not_logged_in():
    """Turn 3b: Check 115 session — not logged in."""
    from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool

    tool = Cloud115Tool(session_path="/tmp/nonexistent_session.json")
    result = await tool.execute(action="check_session")
    data = json.loads(result)
    assert data["logged_in"] is False


@pytest.mark.asyncio
async def test_login_with_qrcode():
    """Turn 3c: Login via QR code (login_with_qrcode flow)."""
    from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool

    tool = Cloud115Tool()
    mock_result = {"data": {"cookie": {"UID": "user1", "CID": "cookie1"}}}
    with patch(
        "p115client.P115Client.login_with_qrcode",
        new_callable=AsyncMock,
        return_value=mock_result,
    ), patch(
        "p115client.P115Client.__init__",
        return_value=None,
    ):
        with patch.object(tool, "_save_session", new_callable=AsyncMock):
            result = await tool.execute(action="login")
            data = json.loads(result)

            assert data["logged_in"] is True
            assert "登录成功" in data["message"]


@pytest.mark.asyncio
async def test_check_session_with_client():
    """Turn 4: Verify session with existing client."""
    from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool

    tool = Cloud115Tool()
    mock_client = MagicMock()
    mock_client.user_info = AsyncMock(return_value={
        "state": True, "data": {"user_name": "test_user"},
    })
    tool._client = mock_client
    result = await tool.execute(action="check_session")
    data = json.loads(result)

    assert data["logged_in"] is True
    assert data["user"] == "test_user"


@pytest.mark.asyncio
async def test_add_magnet_success():
    """Turn 5: Add magnet download task."""
    from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool

    tool = Cloud115Tool()
    tool._client = MagicMock()
    tool._client.offline_add_urls = AsyncMock(
        return_value={
            "state": True,
            "tasks": [{"name": "星际穿越.4K.中英字幕.mkv"}],
        }
    )

    magnet = MOCK_LINKS[0]["magnet"]
    result = await tool.execute(action="add_magnet", magnet_url=magnet)
    data = json.loads(result)

    assert data["success"] is True
    assert "星际穿越" in data["tasks"][0]


@pytest.mark.asyncio
async def test_full_scenario_a_workflow():
    """End-to-end Scenario A: search → detail → links → login → download."""
    from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool
    from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

    gying = GyingScraperTool()
    cloud115 = Cloud115Tool()

    # Turn 1: Search
    with patch.object(gying, "_search", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_SEARCH_RESULTS
        r1 = json.loads(await gying.execute(action="search", query="星际穿越"))
    assert len(r1["results"]) == 2
    selected_url = r1["results"][0]["url"]

    # Turn 2: Detail
    with patch.object(gying, "_detail", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_DETAIL
        r2 = json.loads(await gying.execute(action="detail", url=selected_url))
    assert r2["title"] == "星际穿越"

    # Turn 3: Links
    mock_4k_links = [lk for lk in MOCK_LINKS if lk["quality_tab"] == "中字4K"]
    with patch.object(gying, "_links", new_callable=AsyncMock) as mock:
        mock.return_value = mock_4k_links
        r3 = json.loads(await gying.execute(action="links", url=selected_url, quality="4K"))
    assert len(r3["links"]) == 1
    selected_magnet = r3["links"][0]["magnet"]

    # Turn 4: Login (mock login_with_qrcode)
    mock_login_result = {"data": {"cookie": {"UID": "u1"}}}
    with patch(
        "p115client.P115Client.login_with_qrcode",
        new_callable=AsyncMock,
        return_value=mock_login_result,
    ), patch(
        "p115client.P115Client.__init__",
        return_value=None,
    ):
        with patch.object(cloud115, "_save_session", new_callable=AsyncMock):
            r4 = json.loads(await cloud115.execute(action="login"))
    assert r4["logged_in"] is True

    # Attach a mock client for download
    cloud115._client = MagicMock()

    # Turn 5: Download
    cloud115._client.offline_add_urls = AsyncMock(
        return_value={"state": True, "tasks": [{"name": "星际穿越.4K.中英字幕.mkv"}]}
    )
    r5 = json.loads(await cloud115.execute(action="add_magnet", magnet_url=selected_magnet))
    assert r5["success"] is True
