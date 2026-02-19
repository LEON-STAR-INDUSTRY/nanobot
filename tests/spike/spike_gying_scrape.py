"""
Spike U2: Validate Playwright can scrape gying.org SPA.

Run: python tests/spike/spike_gying_scrape.py
Prerequisites: pip install playwright playwright-stealth && playwright install chromium
"""
import asyncio
import json
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
BROWSER_DATA = OUTPUT_DIR / "gying_browser_data"
SELECTORS_FILE = OUTPUT_DIR / "selectors.json"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

results: dict[str, str] = {}

# Selectors discovered from HTML analysis
SEL = {
    # Search results page
    "search_input": 'input[type="search"]',
    "result_items": ".sr_lists .v5d",
    "result_title": ".text b a.d16",
    "result_rating_text": ".text p",
    # Detail page
    "detail_title": ".main-ui-meta h1 div",
    "detail_year": ".main-ui-meta h1 span.year",
    "detail_rating": ".ratings-section .freshness",
    "detail_genres": '.main-ui-meta a[href*="genre="]',
    "detail_actors": '.main-ui-meta a[href*="/s/2---1/"]',
    "detail_synopsis": ".movie-introduce .zkjj_a",
    "detail_poster": ".main-meta .img img",
    # Download section
    "download_section": "div#down",
    "download_quality_tabs": ".down-link .nav-tabs li",
    "download_rows": "table.bit_list tbody tr",
    "magnet_link": 'a.torrent[href^="magnet:"]',
    # Homepage listing
    "listing_items": "ul.content-list li",
    "listing_title": ".li-bottom h3 a",
    "listing_rating": ".li-bottom h3 span",
    "listing_tag": ".li-bottom div.tag",
    "listing_movie_link": 'a[href^="/mv/"]',
}


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[FAIL] Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    try:
        from playwright_stealth import stealth_async
    except ImportError:
        stealth_async = None
        print("[WARN] playwright-stealth not installed. Anti-detection may fail.")

    print("[INFO] Playwright available")

    async with async_playwright() as p:
        # --- Step 1: Launch browser ---
        print("\n--- Step 1: Browser Launch + Stealth ---")
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_DATA),
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            if stealth_async:
                await stealth_async(page)
            else:
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}};
                """)
            results["browser_launch"] = "PASS"
            print("[PASS] Browser launched with stealth")
        except Exception as e:
            results["browser_launch"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Browser launch: {e}")
            return

        # --- Step 2: Navigate to homepage ---
        print("\n--- Step 2: Navigate to gying.org ---")
        try:
            await page.goto("https://www.gying.org/", wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(SCREENSHOTS_DIR / "01_homepage.png"))
            content = await page.content()
            if len(content) > 500:
                results["page_render"] = "PASS"
                print(f"[PASS] Page rendered ({len(content)} chars)")
            else:
                results["page_render"] = f"FAIL (only {len(content)} chars)"
                print(f"[FAIL] Page too short: {len(content)} chars")

            page_text = await page.inner_text("body")
            if "cloudflare" in page_text.lower() or "checking your browser" in page_text.lower():
                print("[WARN] Cloudflare challenge detected — waiting 10s...")
                await page.wait_for_timeout(10000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "01b_after_cf.png"))
        except Exception as e:
            results["page_render"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Navigation: {e}")

        # --- Step 3: Check auth status ---
        print("\n--- Step 3: Auth Check ---")
        try:
            cookies = await browser.cookies()
            gying_cookies = [c for c in cookies if "gying" in c.get("domain", "")]
            print(f"[INFO] gying cookies: {len(gying_cookies)}")
            user_elem = await page.query_selector('[class*="user"], [class*="profile"]')
            if user_elem:
                results["login"] = "PASS (already authenticated)"
                print("[PASS] Logged in")
            else:
                print("[INFO] Waiting 30s for manual login if needed...")
                await page.wait_for_timeout(30000)
                results["login"] = "MANUAL (check browser)"
        except Exception as e:
            results["login"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Auth check: {e}")

        # --- Step 4: Search ---
        print("\n--- Step 4: Search ---")
        search_query = "星际穿越"
        first_result_url = None
        try:
            search_input = await page.query_selector(SEL["search_input"])
            if not search_input:
                results["search"] = "FAIL (search input not found)"
                print("[FAIL] Search input not found")
            else:
                await search_input.click()
                await search_input.fill(search_query)
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "03_search_results.png"))

                items = await page.query_selector_all(SEL["result_items"])
                if not items:
                    results["search"] = "FAIL (no .v5d result items)"
                    print("[FAIL] No result items found with .sr_lists .v5d")
                else:
                    search_results = []
                    for item in items[:5]:
                        title_el = await item.query_selector(SEL["result_title"])
                        title = await title_el.inner_text() if title_el else "?"
                        href = await title_el.get_attribute("href") if title_el else ""
                        # Rating is in 4th <p> (评分：豆瓣 X.X ...)
                        rating_ps = await item.query_selector_all(SEL["result_rating_text"])
                        rating = ""
                        for rp in rating_ps:
                            text = await rp.inner_text()
                            if text.startswith("评分："):
                                rating = text
                                break
                        search_results.append({
                            "title": title.strip(),
                            "url": href,
                            "rating": rating[:50],
                        })
                    if not first_result_url and search_results:
                        first_result_url = search_results[0]["url"]

                    print(f"[PASS] Found {len(items)} results for '{search_query}'")
                    for sr in search_results:
                        print(f"  - {sr['title']}: {sr['url']}  {sr['rating']}")
                    results["search"] = f"PASS ({len(items)} results)"
        except Exception as e:
            results["search"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Search: {e}")

        # --- Step 5: Detail page ---
        print("\n--- Step 5: Detail Page ---")
        try:
            if not first_result_url:
                results["detail"] = "SKIP (no search result URL)"
                print("[SKIP] No URL to navigate to")
            else:
                # Navigate to detail page via URL (more reliable than clicking)
                detail_url = first_result_url
                if not detail_url.startswith("http"):
                    detail_url = "https://www.gying.org" + detail_url
                await page.goto(detail_url, wait_until="networkidle", timeout=30000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "04_detail_page.png"))

                detail = {}
                # Title
                el = await page.query_selector(SEL["detail_title"])
                if el:
                    detail["title"] = (await el.inner_text()).strip()
                # Year
                el = await page.query_selector(SEL["detail_year"])
                if el:
                    detail["year"] = (await el.inner_text()).strip()
                # Ratings (first = douban, second = IMDb)
                ratings = await page.query_selector_all(SEL["detail_rating"])
                if ratings:
                    detail["douban_rating"] = (await ratings[0].inner_text()).strip()
                if len(ratings) > 1:
                    detail["imdb_rating"] = (await ratings[1].inner_text()).strip()
                # Genres
                genres = await page.query_selector_all(SEL["detail_genres"])
                if genres:
                    detail["genres"] = [
                        (await g.inner_text()).strip() for g in genres
                    ]
                # Synopsis
                el = await page.query_selector(SEL["detail_synopsis"])
                if el:
                    detail["synopsis"] = (await el.inner_text()).strip()[:120] + "..."
                # Poster
                el = await page.query_selector(SEL["detail_poster"])
                if el:
                    detail["poster_src"] = await el.get_attribute("src") or ""

                if detail:
                    print(f"[PASS] Detail: {json.dumps(detail, ensure_ascii=False)[:300]}")
                    results["detail"] = f"PASS ({', '.join(detail.keys())})"
                else:
                    results["detail"] = "FAIL (no fields extracted)"
                    print("[FAIL] No detail fields extracted")
        except Exception as e:
            results["detail"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Detail: {e}")

        # --- Step 6: Download links ---
        print("\n--- Step 6: Download Links ---")
        try:
            download_section = await page.query_selector(SEL["download_section"])
            if not download_section:
                results["links"] = "FAIL (div#down not found)"
                print("[FAIL] Download section not found")
            else:
                print("[INFO] Download section found: div#down")

                # Check quality tabs
                tabs = await page.query_selector_all(SEL["download_quality_tabs"])
                tab_labels = []
                for tab in tabs:
                    text = (await tab.inner_text()).strip()
                    tab_labels.append(text)
                print(f"[INFO] Quality tabs: {tab_labels}")

                # Extract magnet links from table rows
                rows = await page.query_selector_all(SEL["download_rows"])
                link_data = []
                for row in rows:
                    magnet_el = await row.query_selector(SEL["magnet_link"])
                    if magnet_el:
                        name = (await magnet_el.inner_text()).strip()
                        magnet = await magnet_el.get_attribute("href") or ""
                        # Get size from 3rd <td>
                        tds = await row.query_selector_all("td")
                        size = ""
                        if len(tds) >= 3:
                            size = (await tds[2].inner_text()).strip()
                        link_data.append({
                            "name": name[:80],
                            "magnet": magnet[:80] + "..." if len(magnet) > 80 else magnet,
                            "size": size,
                        })

                if link_data:
                    # Classify by quality (check filename for 4K/2160p/1080p and 中字/中文)
                    links_4k_cn = [
                        lk for lk in link_data
                        if ("4K" in lk["name"] or "2160p" in lk["name"])
                        and ("中字" in lk["name"] or "中文" in lk["name"])
                    ]
                    links_1080_cn = [
                        lk for lk in link_data
                        if "1080p" in lk["name"].lower()
                        and ("中字" in lk["name"] or "中文" in lk["name"])
                    ]
                    print(f"[PASS] Found {len(link_data)} magnet links")
                    print(f"  - 中字4K: {len(links_4k_cn)}")
                    print(f"  - 中字1080P: {len(links_1080_cn)}")
                    for lk in link_data[:5]:
                        print(f"  - [{lk['size']}] {lk['name']}")
                    results["links"] = (
                        f"PASS ({len(link_data)} total, "
                        f"{len(links_4k_cn)}×中字4K, {len(links_1080_cn)}×中字1080P)"
                    )
                else:
                    results["links"] = "FAIL (no magnet links in table)"
                    print("[FAIL] No magnet links found in table rows")
        except Exception as e:
            results["links"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Links: {e}")

        # --- Step 7: Homepage listing ---
        print("\n--- Step 7: Homepage Listing ---")
        try:
            await page.goto("https://www.gying.org/", wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(SCREENSHOTS_DIR / "05_listing_page.png"))

            items = await page.query_selector_all(SEL["listing_items"])
            if not items:
                results["listing"] = "FAIL (no ul.content-list li)"
                print("[FAIL] No listing items found")
            else:
                listing_data = []
                movie_count = 0
                tv_count = 0
                for item in items[:24]:  # Limit to avoid too many
                    title_el = await item.query_selector(SEL["listing_title"])
                    title = (await title_el.inner_text()).strip() if title_el else "?"
                    href = (await title_el.get_attribute("href") or "") if title_el else ""
                    rating_el = await item.query_selector(SEL["listing_rating"])
                    rating = (await rating_el.inner_text()).strip() if rating_el else ""
                    tag_el = await item.query_selector(SEL["listing_tag"])
                    tag = (await tag_el.inner_text()).strip() if tag_el else ""
                    is_movie = href.startswith("/mv/")
                    if is_movie:
                        movie_count += 1
                    else:
                        tv_count += 1
                    listing_data.append({
                        "title": title,
                        "url": href,
                        "rating": rating,
                        "tag": tag[:40],
                        "type": "movie" if is_movie else "tv",
                    })

                print(f"[PASS] Listing: {len(listing_data)} items ({movie_count} movies, {tv_count} TV)")
                for item_data in listing_data[:6]:
                    marker = "M" if item_data["type"] == "movie" else "T"
                    print(
                        f"  [{marker}] {item_data['title']} ({item_data['rating']}) "
                        f"- {item_data['tag']}"
                    )
                results["listing"] = (
                    f"PASS ({len(listing_data)} items: {movie_count} movies, {tv_count} TV)"
                )
        except Exception as e:
            results["listing"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Listing: {e}")

        # --- Step 8: Save selectors & browser state ---
        print("\n--- Step 8: Save ---")
        SELECTORS_FILE.write_text(json.dumps(SEL, ensure_ascii=False, indent=2))
        print(f"[INFO] Selectors saved to {SELECTORS_FILE}")

        storage = await browser.storage_state()
        storage_file = OUTPUT_DIR / "gying_storage_state.json"
        storage_file.write_text(json.dumps(storage, ensure_ascii=False, indent=2))
        print(f"[INFO] Storage state saved to {storage_file}")

        await browser.close()

    # --- Summary ---
    print("\n" + "=" * 60)
    print("SPIKE U2 RESULTS SUMMARY")
    print("=" * 60)
    for key, val in results.items():
        status = "PASS" if "PASS" in val else ("SKIP" if "SKIP" in val else "FAIL")
        print(f"[{status}] {key}: {val}")
    print("=" * 60)

    results_file = OUTPUT_DIR / "spike_u2_results.json"
    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
