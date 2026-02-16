"""GyingScraperTool: Playwright-based gying.org scraper."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool

# CSS selectors for gying.org (validated in spike U2)
SELECTORS = {
    "search_input": 'input[type="search"]',
    "result_items": ".sr_lists .v5d",
    "result_title": ".text b a.d16",
    "result_rating_text": ".text p",
    "detail_title": ".main-ui-meta h1 div",
    "detail_year": ".main-ui-meta h1 span.year",
    "detail_rating": ".ratings-section .freshness",
    "detail_genres": '.main-ui-meta a[href*="genre="]',
    "detail_actors": '.main-ui-meta a[href*="/s/2---1/"]',
    "detail_synopsis": ".movie-introduce .zkjj_a",
    "detail_poster": ".main-meta .img img",
    "download_section": "div#down",
    "download_quality_tabs": ".down-link .nav-tabs li",
    "download_rows": "table.bit_list tbody tr",
    "magnet_link": 'a.torrent[href^="magnet:"]',
    "listing_items": "ul.content-list li",
    "listing_title": ".li-bottom h3 a",
    "listing_rating": ".li-bottom h3 span",
    "listing_tag": ".li-bottom div.tag",
}

BASE_URL = "https://www.gying.org"


class GyingScraperTool(Tool):
    """Tool for scraping movie data from gying.org using Playwright."""

    def __init__(
        self,
        browser_data_dir: str = "",
        headless: bool = True,
    ):
        self._browser_data_dir = browser_data_dir
        self._headless = headless
        self._browser = None
        self._page = None

    @property
    def name(self) -> str:
        return "gying_search"

    @property
    def description(self) -> str:
        return (
            "Search and scrape movie information from gying.org. Actions: "
            "search (search movies by keyword), "
            "detail (get movie detail info by URL), "
            "links (get download magnet links for a movie)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "detail", "links"],
                    "description": "Action to perform.",
                },
                "query": {
                    "type": "string",
                    "description": "Search keyword (required for search).",
                },
                "url": {
                    "type": "string",
                    "description": "Movie detail page URL (required for detail/links).",
                },
                "quality": {
                    "type": "string",
                    "description": "Quality filter: '4K', '1080P', or empty for all.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        try:
            if action == "search":
                query = kwargs.get("query", "")
                if not query:
                    return json.dumps(
                        {"error": "缺少query参数，请提供搜索关键词"}, ensure_ascii=False
                    )
                results = await self._search(query)
                return json.dumps({"results": results}, ensure_ascii=False)
            elif action == "detail":
                url = kwargs.get("url", "")
                if not url:
                    return json.dumps(
                        {"error": "缺少url参数，请提供影片详情页URL"}, ensure_ascii=False
                    )
                detail = await self._detail(url)
                return json.dumps(detail, ensure_ascii=False)
            elif action == "links":
                url = kwargs.get("url", "")
                if not url:
                    return json.dumps(
                        {"error": "缺少url参数，请提供影片详情页URL"}, ensure_ascii=False
                    )
                quality = kwargs.get("quality", "")
                all_links = await self._links(url)
                result = {"links": all_links}
                if quality:
                    filtered = [
                        lk for lk in all_links
                        if quality.upper() in lk.get("name", "").upper()
                    ]
                    result["filtered"] = filtered
                    result["filter"] = quality
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({"error": f"未知操作: {action}"}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"GyingScraperTool error: {e}")
            return json.dumps(
                {"error": f"抓取失败: {type(e).__name__}: {e}"}, ensure_ascii=False
            )

    # ------------------------------------------------------------------
    # Browser management
    # ------------------------------------------------------------------

    async def _ensure_browser(self):
        """Lazy-launch browser on first use."""
        if self._page:
            return

        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        launch_args = {
            "headless": self._headless,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            "locale": "zh-CN",
            "viewport": {"width": 1280, "height": 800},
        }
        if self._browser_data_dir:
            launch_args["user_data_dir"] = self._browser_data_dir

        self._browser = await pw.chromium.launch_persistent_context(**launch_args)
        self._page = self._browser.pages[0] if self._browser.pages else await self._browser.new_page()

        # Apply stealth
        try:
            from playwright_stealth import stealth_async

            await stealth_async(self._page)
        except ImportError:
            await self._page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}};
            """)

        logger.info("Playwright browser launched for gying.org")

    async def close(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None

    # ------------------------------------------------------------------
    # Scraping methods
    # ------------------------------------------------------------------

    async def _search(self, query: str) -> list[dict]:
        """Search gying.org for movies."""
        await self._ensure_browser()
        page = self._page

        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        search_input = await page.query_selector(SELECTORS["search_input"])
        if not search_input:
            raise RuntimeError("搜索框未找到")

        await search_input.click()
        await search_input.fill(query)
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle", timeout=15000)

        items = await page.query_selector_all(SELECTORS["result_items"])
        results = []
        for item in items[:10]:
            title_el = await item.query_selector(SELECTORS["result_title"])
            title = (await title_el.inner_text()).strip() if title_el else "?"
            href = (await title_el.get_attribute("href") or "") if title_el else ""

            rating = ""
            rating_ps = await item.query_selector_all(SELECTORS["result_rating_text"])
            for rp in rating_ps:
                text = await rp.inner_text()
                if text.startswith("评分："):
                    rating = text.replace("评分：", "").strip()
                    break

            results.append({"title": title, "url": href, "rating": rating})

        return results

    async def _detail(self, url: str) -> dict:
        """Get movie detail from gying.org."""
        await self._ensure_browser()
        page = self._page

        full_url = url if url.startswith("http") else BASE_URL + url
        await page.goto(full_url, wait_until="networkidle", timeout=30000)

        detail = {}

        el = await page.query_selector(SELECTORS["detail_title"])
        if el:
            detail["title"] = (await el.inner_text()).strip()

        el = await page.query_selector(SELECTORS["detail_year"])
        if el:
            detail["year"] = (await el.inner_text()).strip()

        ratings = await page.query_selector_all(SELECTORS["detail_rating"])
        if ratings:
            detail["douban_rating"] = (await ratings[0].inner_text()).strip()
        if len(ratings) > 1:
            detail["imdb_rating"] = (await ratings[1].inner_text()).strip()

        genres = await page.query_selector_all(SELECTORS["detail_genres"])
        if genres:
            detail["genres"] = [(await g.inner_text()).strip() for g in genres]

        el = await page.query_selector(SELECTORS["detail_synopsis"])
        if el:
            detail["synopsis"] = (await el.inner_text()).strip()

        el = await page.query_selector(SELECTORS["detail_poster"])
        if el:
            detail["poster"] = await el.get_attribute("src") or ""

        detail["url"] = url
        return detail

    async def _links(self, url: str) -> list[dict]:
        """Get magnet download links from a movie detail page."""
        await self._ensure_browser()
        page = self._page

        # Navigate if not already on the right page
        current = page.url
        full_url = url if url.startswith("http") else BASE_URL + url
        if full_url not in current:
            await page.goto(full_url, wait_until="networkidle", timeout=30000)

        rows = await page.query_selector_all(SELECTORS["download_rows"])
        links = []
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
            })

        return links


class GyingUpdatesTool(Tool):
    """Tool for checking gying.org for new movie releases."""

    def __init__(
        self,
        seen_file: str = "",
        browser_data_dir: str = "",
        headless: bool = True,
    ):
        self._seen_file = Path(seen_file) if seen_file else None
        self._browser_data_dir = browser_data_dir
        self._headless = headless
        self._scraper: GyingScraperTool | None = None

    @property
    def name(self) -> str:
        return "gying_check_updates"

    @property
    def description(self) -> str:
        return (
            "Check gying.org for new movie releases. "
            "Compares against seen_movies.json and returns only unseen entries."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["latest", "trending", "4k", "all"],
                    "description": "Which listing page to check.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of new movies to return.",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        try:
            max_results = kwargs.get("max_results", 10)
            listing = await self._scrape_listing()

            seen_data = self._load_seen()
            seen_urls = set(seen_data.get("movies", {}).keys())

            new_movies = []
            for item in listing:
                url = item.get("url", "")
                if url not in seen_urls:
                    new_movies.append(item)

            total = len(listing)
            previously_seen = total - len(new_movies)

            # Limit results
            new_movies = new_movies[:max_results]

            # Update seen file
            now = datetime.now(timezone.utc).isoformat()
            movies_dict = seen_data.get("movies", {})
            for movie in new_movies:
                url = movie.get("url", "")
                if url:
                    movies_dict[url] = {
                        "title": movie.get("title", ""),
                        "first_seen": now[:10],
                        "notified": True,
                    }
            seen_data["movies"] = movies_dict
            seen_data["last_check"] = now
            self._cleanup_seen(seen_data)
            self._save_seen(seen_data)

            return json.dumps({
                "new_movies": new_movies,
                "total_checked": total,
                "previously_seen": previously_seen,
                "new_count": len(new_movies),
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"GyingUpdatesTool error: {e}")
            return json.dumps(
                {"error": f"检查更新失败: {type(e).__name__}: {e}"}, ensure_ascii=False
            )

    async def _scrape_listing(self) -> list[dict]:
        """Scrape the homepage listing from gying.org."""
        if not self._scraper:
            self._scraper = GyingScraperTool(
                browser_data_dir=self._browser_data_dir,
                headless=self._headless,
            )
        await self._scraper._ensure_browser()
        page = self._scraper._page

        await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

        items = await page.query_selector_all(SELECTORS["listing_items"])
        results = []
        for item in items:
            title_el = await item.query_selector(SELECTORS["listing_title"])
            title = (await title_el.inner_text()).strip() if title_el else ""
            href = (await title_el.get_attribute("href") or "") if title_el else ""

            rating_el = await item.query_selector(SELECTORS["listing_rating"])
            rating = (await rating_el.inner_text()).strip() if rating_el else ""

            tag_el = await item.query_selector(SELECTORS["listing_tag"])
            tag = (await tag_el.inner_text()).strip() if tag_el else ""

            if title and href:
                results.append({
                    "title": title,
                    "url": href,
                    "rating": rating,
                    "tag": tag,
                })

        return results

    def _load_seen(self) -> dict:
        """Load seen_movies.json."""
        if not self._seen_file or not self._seen_file.exists():
            return {"movies": {}, "last_check": ""}
        try:
            return json.loads(self._seen_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"movies": {}, "last_check": ""}

    def _cleanup_seen(self, data: dict, max_age_days: int = 90) -> None:
        """Remove entries older than max_age_days from seen data (in-place)."""
        movies = data.get("movies", {})
        if not movies:
            return
        today = datetime.now(timezone.utc).date()
        to_remove = []
        for url, info in movies.items():
            first_seen = info.get("first_seen", "")
            if not first_seen:
                continue
            try:
                seen_date = datetime.strptime(first_seen, "%Y-%m-%d").date()
                if (today - seen_date).days > max_age_days:
                    to_remove.append(url)
            except ValueError:
                continue
        for url in to_remove:
            del movies[url]

    def _save_seen(self, data: dict) -> None:
        """Save seen_movies.json."""
        if not self._seen_file:
            return
        self._seen_file.parent.mkdir(parents=True, exist_ok=True)
        self._seen_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
