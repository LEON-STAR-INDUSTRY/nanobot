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

# Known selectors (to be discovered and updated during spike)
SELECTORS: dict[str, str] = {
    "search_input": "",
    "result_items": "",
    "detail_title": "",
    "detail_rating": "",
    "detail_genres": "",
    "detail_actors": "",
    "detail_synopsis": "",
    "detail_poster": "",
    "download_section": "",
    "download_rows": "",
    "magnet_link": "",
    "listing_items": "",
    "listing_title": "",
    "listing_url": "",
    "listing_rating": "",
}


async def main():
    # Step 1: Check Playwright is installed
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
        print("[WARN] Install: pip install playwright-stealth")

    print("[INFO] Playwright available")

    async with async_playwright() as p:
        # Step 2: Launch browser with stealth
        print("\n--- Step 2: Browser Launch + Stealth ---")
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_DATA),
                headless=False,  # Use headed mode for initial spike (need to see what happens)
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                locale="zh-CN",
                viewport={"width": 1280, "height": 800},
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()

            # Apply stealth if available
            if stealth_async:
                await stealth_async(page)
            else:
                # Manual anti-detection
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

        # Step 2b: Navigate to gying.org
        print("\n--- Step 2b: Navigate to gying.org ---")
        try:
            await page.goto("https://www.gying.org/", wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(SCREENSHOTS_DIR / "01_homepage.png"))

            # Check if page rendered
            content = await page.content()
            if len(content) > 500:
                results["page_render"] = "PASS"
                print(f"[PASS] Page rendered ({len(content)} chars)")
            else:
                results["page_render"] = f"FAIL (only {len(content)} chars)"
                print(f"[FAIL] Page too short: {len(content)} chars")

            # Detect: login page, Cloudflare challenge, or content
            page_text = await page.inner_text("body")
            if "cloudflare" in page_text.lower() or "checking your browser" in page_text.lower():
                print("[WARN] Cloudflare challenge detected — waiting 10s...")
                await page.wait_for_timeout(10000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "01b_after_cf.png"))
                page_text = await page.inner_text("body")

            if "登录" in page_text and "注册" in page_text and len(page_text) < 500:
                print("[INFO] Login page detected")
                results["auth_status"] = "NEEDS_LOGIN"
            else:
                print("[INFO] Content page detected (may be logged in or public)")
                results["auth_status"] = "CONTENT_VISIBLE"

        except Exception as e:
            results["page_render"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Navigation: {e}")

        # Step 3: Investigate login flow
        print("\n--- Step 3: Login Flow Investigation ---")
        try:
            # Check cookies for existing session
            cookies = await browser.cookies()
            session_cookies = [c for c in cookies if "gying" in c.get("domain", "")]
            print(f"[INFO] Existing gying cookies: {len(session_cookies)}")
            for c in session_cookies[:5]:
                print(f"  - {c['name']}: {c['value'][:20]}...")

            # Look for login-related elements
            login_btn = await page.query_selector('a[href*="login"], button:has-text("登录")')
            if login_btn:
                print("[INFO] Login button found")
                login_text = await login_btn.inner_text()
                print(f"[INFO] Login button text: {login_text}")
            else:
                print("[INFO] No login button visible (might already be logged in)")

            # Check for user profile element (indicates logged in)
            user_elem = await page.query_selector(
                '.user-info, .avatar, [class*="user"], [class*="profile"]'
            )
            if user_elem:
                print("[INFO] User profile element found — likely logged in")
                results["login"] = "PASS (already authenticated)"
            else:
                print("[INFO] No user profile element — may need to login manually")
                print("[INFO] If login is needed, use the browser window to log in now...")
                print("[INFO] Waiting 30s for manual login (if needed)...")
                await page.wait_for_timeout(30000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "02_after_login_wait.png"))
                results["login"] = "MANUAL (check screenshot)"

        except Exception as e:
            results["login"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Login investigation: {e}")

        # Step 4: Search
        print("\n--- Step 4: Search ---")
        search_query = "星际穿越"
        try:
            # Try common search selectors
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="搜索"]',
                'input[placeholder*="search"]',
                'input[name="q"]',
                'input[name="search"]',
                'input[name="keyword"]',
                ".search-input input",
                "#search-input",
                'input[class*="search"]',
            ]
            search_input = None
            for sel in search_selectors:
                search_input = await page.query_selector(sel)
                if search_input:
                    SELECTORS["search_input"] = sel
                    print(f"[INFO] Search input found: {sel}")
                    break

            if not search_input:
                # Try finding any visible input
                all_inputs = await page.query_selector_all("input[type='text'], input:not([type])")
                if all_inputs:
                    search_input = all_inputs[0]
                    SELECTORS["search_input"] = "input (first text input)"
                    print(f"[INFO] Using first text input as search (found {len(all_inputs)} inputs)")

            if search_input:
                await search_input.click()
                await search_input.fill(search_query)
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "03_search_results.png"))

                # Extract results
                result_selectors = [
                    ".movie-item",
                    ".search-result",
                    ".result-item",
                    ".item",
                    'a[href*="movie"]',
                    'a[href*="detail"]',
                    ".card",
                    ".list-item",
                ]
                result_items = []
                for sel in result_selectors:
                    items = await page.query_selector_all(sel)
                    if len(items) >= 1:
                        SELECTORS["result_items"] = sel
                        result_items = items
                        print(f"[INFO] Result items found with selector: {sel} ({len(items)} items)")
                        break

                if result_items:
                    # Extract info from first few results
                    search_results = []
                    for item in result_items[:5]:
                        title_el = await item.query_selector(
                            "h2, h3, h4, .title, [class*='title'], a"
                        )
                        title = await title_el.inner_text() if title_el else "unknown"
                        href_el = await item.query_selector("a[href]")
                        href = await href_el.get_attribute("href") if href_el else ""
                        search_results.append({"title": title.strip(), "url": href})

                    print(f"[PASS] Search found {len(search_results)} results for '{search_query}'")
                    for r in search_results:
                        print(f"  - {r['title']}: {r['url']}")
                    results["search"] = f"PASS ({len(search_results)} results)"
                else:
                    # Dump page content for debugging
                    page_text = await page.inner_text("body")
                    print(f"[FAIL] No result items found. Page text preview: {page_text[:300]}")
                    results["search"] = "FAIL (no result items found)"
            else:
                print("[FAIL] No search input found")
                results["search"] = "FAIL (no search input)"

        except Exception as e:
            results["search"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Search: {e}")

        # Step 5: Detail page extraction
        print("\n--- Step 5: Detail Page Extraction ---")
        try:
            # Click first search result
            if SELECTORS.get("result_items"):
                first_result_link = await page.query_selector(
                    f'{SELECTORS["result_items"]} a[href]'
                )
                if first_result_link:
                    await first_result_link.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await page.screenshot(path=str(SCREENSHOTS_DIR / "04_detail_page.png"))

                    # Extract detail info
                    detail_selectors = {
                        "detail_title": ["h1", ".title", ".movie-title", "[class*='title']"],
                        "detail_rating": [
                            ".rating",
                            ".score",
                            "[class*='rating']",
                            "[class*='score']",
                        ],
                        "detail_genres": [
                            ".genres",
                            ".genre",
                            "[class*='genre']",
                            "[class*='tag']",
                        ],
                        "detail_synopsis": [
                            ".synopsis",
                            ".description",
                            ".summary",
                            "[class*='desc']",
                            "[class*='synopsis']",
                        ],
                    }

                    detail_data = {}
                    for field, sels in detail_selectors.items():
                        for sel in sels:
                            el = await page.query_selector(sel)
                            if el:
                                text = await el.inner_text()
                                if text.strip():
                                    detail_data[field] = text.strip()[:100]
                                    SELECTORS[field] = sel
                                    break

                    if detail_data:
                        print(f"[PASS] Detail extracted: {json.dumps(detail_data, ensure_ascii=False)}")
                        results["detail"] = f"PASS ({', '.join(detail_data.keys())})"
                    else:
                        results["detail"] = "FAIL (no detail fields extracted)"
                        print("[FAIL] Could not extract detail fields")
                else:
                    results["detail"] = "FAIL (no result link to click)"
            else:
                results["detail"] = "SKIP (no search results)"

        except Exception as e:
            results["detail"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Detail: {e}")

        # Step 6: Download links extraction
        print("\n--- Step 6: Download Links Extraction ---")
        try:
            # Look for download section
            download_selectors = [
                ".download",
                ".downloads",
                "[class*='download']",
                "#download",
                "table",
                ".magnet",
                "[class*='magnet']",
            ]
            download_section = None
            for sel in download_selectors:
                download_section = await page.query_selector(sel)
                if download_section:
                    SELECTORS["download_section"] = sel
                    print(f"[INFO] Download section found: {sel}")
                    break

            # Extract all links
            all_links = await page.query_selector_all('a[href*="magnet:"]')
            if not all_links:
                # Try finding magnet links in onclick or data attributes
                all_links = await page.query_selector_all(
                    'a[data-clipboard-text*="magnet:"], [onclick*="magnet:"]'
                )

            if all_links:
                link_data = []
                for link in all_links:
                    href = await link.get_attribute("href") or ""
                    clipboard = await link.get_attribute("data-clipboard-text") or ""
                    text = await link.inner_text()
                    magnet = href if href.startswith("magnet:") else clipboard
                    link_data.append({
                        "label": text.strip()[:80],
                        "magnet": magnet[:80] + "..." if len(magnet) > 80 else magnet,
                    })

                # Filter for quality
                links_4k = [lk for lk in link_data if "4K" in lk["label"] and "中字" in lk["label"]]
                links_1080 = [
                    lk for lk in link_data if "1080" in lk["label"] and "中字" in lk["label"]
                ]

                print(f"[PASS] Found {len(link_data)} total links")
                print(f"  - 4K+中字: {len(links_4k)}")
                print(f"  - 1080P+中字: {len(links_1080)}")
                for lk in link_data[:5]:
                    print(f"  - {lk['label']}: {lk['magnet']}")
                results["links"] = (
                    f"PASS ({len(link_data)} total, {len(links_4k)}×4K中字, "
                    f"{len(links_1080)}×1080P中字)"
                )
            else:
                print("[FAIL] No magnet links found")
                # Dump page for debugging
                page_text = await page.inner_text("body")
                print(f"[INFO] Page text preview: {page_text[:500]}")
                results["links"] = "FAIL (no magnet links)"

        except Exception as e:
            results["links"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Links: {e}")

        # Step 7: Latest/trending listing page
        print("\n--- Step 7: Latest Listing Page ---")
        try:
            # Navigate to homepage or latest page
            await page.goto("https://www.gying.org/", wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(SCREENSHOTS_DIR / "05_listing_page.png"))

            # Look for movie listing items
            listing_selectors = [
                ".movie-item",
                ".card",
                ".item",
                ".list-item",
                'a[href*="movie"]',
                'a[href*="detail"]',
                ".post",
                "article",
            ]
            listing_items = []
            for sel in listing_selectors:
                items = await page.query_selector_all(sel)
                if len(items) >= 3:
                    SELECTORS["listing_items"] = sel
                    listing_items = items
                    print(f"[INFO] Listing items found: {sel} ({len(items)} items)")
                    break

            if listing_items:
                listing_data = []
                for item in listing_items[:10]:
                    title_el = await item.query_selector(
                        "h2, h3, h4, .title, [class*='title'], a"
                    )
                    title = await title_el.inner_text() if title_el else "unknown"
                    href_el = await item.query_selector("a[href]")
                    href = await href_el.get_attribute("href") if href_el else ""
                    listing_data.append({"title": title.strip()[:60], "url": href})

                print(f"[PASS] Latest listing: {len(listing_data)} movies")
                for m in listing_data[:5]:
                    print(f"  - {m['title']}: {m['url']}")
                results["listing"] = f"PASS ({len(listing_data)} movies)"
            else:
                results["listing"] = "FAIL (no listing items)"
                print("[FAIL] No listing items found")

        except Exception as e:
            results["listing"] = f"FAIL ({type(e).__name__}: {e})"
            print(f"[FAIL] Listing: {e}")

        # Step 8: Save selectors
        print("\n--- Step 8: Save Selectors ---")
        SELECTORS_FILE.write_text(json.dumps(SELECTORS, ensure_ascii=False, indent=2))
        print(f"[INFO] Selectors saved to {SELECTORS_FILE}")

        # Save browser state (cookies)
        storage = await browser.storage_state()
        storage_file = OUTPUT_DIR / "gying_storage_state.json"
        storage_file.write_text(json.dumps(storage, ensure_ascii=False, indent=2))
        print(f"[INFO] Storage state saved to {storage_file}")

        await browser.close()

    # Print summary
    print("\n" + "=" * 60)
    print("SPIKE U2 RESULTS SUMMARY")
    print("=" * 60)
    for key, val in results.items():
        status = "PASS" if "PASS" in val else ("SKIP" if "SKIP" in val else "FAIL")
        print(f"[{status}] {key}: {val}")
    print("=" * 60)

    # Save results
    results_file = OUTPUT_DIR / "spike_u2_results.json"
    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
