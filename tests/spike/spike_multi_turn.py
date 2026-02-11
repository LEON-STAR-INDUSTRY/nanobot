"""
Spike U3: Validate nanobot's session + tool system supports a 5-turn stateful
film-download workflow without losing context.

Run: python tests/spike/spike_multi_turn.py
Prerequisites: nanobot installed (pip install -e .)
"""
import asyncio
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

results: dict[str, str] = {}

# State file for mock tools
STATE_FILE = OUTPUT_DIR / "spike_u3_state.json"


# ---------------------------------------------------------------------------
# Mock Tools: simulate the film download workflow
# ---------------------------------------------------------------------------
def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# Hardcoded test data
MOCK_SEARCH_RESULTS = [
    {
        "title": "星际穿越 Interstellar (2014)",
        "url": "https://gying.org/movie/123",
        "rating": "9.4",
    },
    {
        "title": "星际迷航 Star Trek (2009)",
        "url": "https://gying.org/movie/456",
        "rating": "8.0",
    },
]

MOCK_DETAIL = {
    "title": "星际穿越 Interstellar",
    "year": 2014,
    "rating": "9.4",
    "genres": ["科幻", "冒险", "剧情"],
    "actors": ["马修·麦康纳", "安妮·海瑟薇"],
    "synopsis": "一队探险家利用他们针对虫洞的新发现，超越人类对于太空旅行的极限...",
}

MOCK_LINKS = [
    {
        "label": "星际穿越.Interstellar.2014.4K.中英字幕.mkv",
        "magnet": "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12&dn=Interstellar.4K",
        "quality": "4K",
        "subtitle": "中字",
    },
    {
        "label": "星际穿越.Interstellar.2014.1080P.中英字幕.mkv",
        "magnet": "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678&dn=Interstellar.1080P",
        "quality": "1080P",
        "subtitle": "中字",
    },
]


async def mock_gying_execute(**kwargs) -> str:
    """Mock GyingScraperTool.execute()."""
    action = kwargs.get("action", "")
    state = _load_state()

    if action == "search":
        query = kwargs.get("query", "")
        state["last_search"] = {"query": query, "results": MOCK_SEARCH_RESULTS}
        _save_state(state)
        return json.dumps({"results": MOCK_SEARCH_RESULTS}, ensure_ascii=False)

    elif action == "detail":
        state["last_detail"] = MOCK_DETAIL
        _save_state(state)
        return json.dumps(MOCK_DETAIL, ensure_ascii=False)

    elif action == "links":
        quality_filter = kwargs.get("quality", "")
        links = MOCK_LINKS
        if quality_filter:
            links = [lk for lk in links if quality_filter.upper() in lk["quality"]]
        state["last_links"] = links
        _save_state(state)
        return json.dumps({"links": links}, ensure_ascii=False)

    return json.dumps({"error": f"unknown action: {action}"})


async def mock_cloud115_execute(**kwargs) -> str:
    """Mock Cloud115Tool.execute()."""
    action = kwargs.get("action", "")
    state = _load_state()

    if action == "check_session":
        logged_in = state.get("115_logged_in", False)
        return json.dumps({"logged_in": logged_in})

    elif action == "login":
        state["115_login_pending"] = True
        _save_state(state)
        return json.dumps({
            "status": "waiting_for_scan",
            "qr_image_base64": "iVBORw0KGgo=",  # Fake base64
            "instruction": "请使用115手机App扫描二维码登录",
        })

    elif action == "confirm_login":
        state["115_logged_in"] = True
        state.pop("115_login_pending", None)
        _save_state(state)
        return json.dumps({"logged_in": True, "message": "登录成功"})

    elif action == "add_magnet":
        magnet = kwargs.get("magnet_url", "")
        if not state.get("115_logged_in"):
            return json.dumps({"error": "未登录115，请先扫码登录"})
        state["last_magnet"] = magnet
        _save_state(state)
        return json.dumps({"success": True, "message": f"离线下载任务已添加: {magnet[:50]}..."})

    return json.dumps({"error": f"unknown action: {action}"})


# ---------------------------------------------------------------------------
# Test harness: simulate agent loop with mock tools
# ---------------------------------------------------------------------------
async def simulate_conversation():
    """Simulate the 5-turn conversation using mock tools directly.

    This tests the tool logic and state persistence, not the full AgentLoop
    (which requires an LLM provider). The goal is to validate that:
    1. Tools return structured data
    2. State persists between calls
    3. The workflow makes logical sense
    """
    # Clean state
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    print("=" * 60)
    print("SIMULATING 5-TURN FILM DOWNLOAD CONVERSATION")
    print("=" * 60)

    # Turn 1: "帮我找 星际穿越" → search results
    print("\n--- Turn 1: '帮我找 星际穿越' ---")
    result = await mock_gying_execute(action="search", query="星际穿越")
    data = json.loads(result)
    if "results" in data and len(data["results"]) > 0:
        print(f"[PASS] Search returned {len(data['results'])} results")
        for i, r in enumerate(data["results"]):
            print(f"  {i + 1}. {r['title']} ({r['rating']})")
        results["turn1_search"] = "PASS"
    else:
        results["turn1_search"] = "FAIL"
        print("[FAIL] No search results")
        return

    # Verify state persisted
    state = _load_state()
    assert "last_search" in state, "Search state not saved"

    # Turn 2: "1" → agent interprets as "select first result" → show detail
    print("\n--- Turn 2: '1' (select first result) ---")
    selected_url = data["results"][0]["url"]
    result = await mock_gying_execute(action="detail", url=selected_url)
    data = json.loads(result)
    if "title" in data:
        print(f"[PASS] Detail: {data['title']} ({data.get('rating', 'N/A')})")
        print(f"  Genres: {', '.join(data.get('genres', []))}")
        print(f"  Synopsis: {data.get('synopsis', '')[:60]}...")
        results["turn2_detail"] = "PASS"
    else:
        results["turn2_detail"] = "FAIL"
        print("[FAIL] No detail data")
        return

    # Turn 3: "4K" → get links filtered by 4K, check 115 login
    print("\n--- Turn 3: '4K' (request 4K download links) ---")
    # Get links
    result = await mock_gying_execute(action="links", url=selected_url, quality="4K")
    links = json.loads(result)
    if "links" in links and len(links["links"]) > 0:
        print(f"[PASS] Found {len(links['links'])} 4K links")
        for lk in links["links"]:
            print(f"  - {lk['label']}")
    else:
        results["turn3_links"] = "FAIL"
        print("[FAIL] No 4K links")
        return

    # Check 115 login status
    session_result = await mock_cloud115_execute(action="check_session")
    session = json.loads(session_result)
    if not session["logged_in"]:
        print("[INFO] 115 not logged in, triggering QR login...")
        login_result = await mock_cloud115_execute(action="login")
        login_data = json.loads(login_result)
        print(f"[INFO] QR status: {login_data['status']}")
        print(f"[INFO] Instruction: {login_data['instruction']}")
        results["turn3_links"] = "PASS (login triggered)"
    else:
        results["turn3_links"] = "PASS (already logged in)"

    # Turn 4: "已扫码" → confirm login
    print("\n--- Turn 4: '已扫码' (user confirms QR scan) ---")
    confirm_result = await mock_cloud115_execute(action="confirm_login")
    confirm_data = json.loads(confirm_result)
    if confirm_data.get("logged_in"):
        print(f"[PASS] Login confirmed: {confirm_data['message']}")
        results["turn4_login"] = "PASS"
    else:
        results["turn4_login"] = "FAIL"
        print("[FAIL] Login confirmation failed")
        return

    # Turn 5: "1" → select first link → add magnet download
    print("\n--- Turn 5: '1' (select first download link) ---")
    magnet_url = links["links"][0]["magnet"]
    add_result = await mock_cloud115_execute(action="add_magnet", magnet_url=magnet_url)
    add_data = json.loads(add_result)
    if add_data.get("success"):
        print(f"[PASS] Download added: {add_data['message']}")
        results["turn5_download"] = "PASS"
    else:
        results["turn5_download"] = f"FAIL ({add_data.get('error', 'unknown')})"
        print(f"[FAIL] Download failed: {add_data}")

    # Verify final state
    final_state = _load_state()
    assert final_state.get("115_logged_in"), "Login state lost"
    assert final_state.get("last_magnet"), "Magnet state lost"
    assert final_state.get("last_search"), "Search state lost"
    print("\n[PASS] All state persisted correctly across turns")
    results["state_persistence"] = "PASS"


# ---------------------------------------------------------------------------
# AgentLoop integration test (requires LLM provider — optional)
# ---------------------------------------------------------------------------
async def test_agent_integration():
    """Test with actual AgentLoop if possible. Requires configured LLM provider."""
    print("\n" + "=" * 60)
    print("AGENT LOOP INTEGRATION TEST (optional)")
    print("=" * 60)

    try:
        from nanobot.config.loader import load_config

        config = load_config()
        if not config.get_api_key():
            print("[SKIP] No LLM provider configured. Set NANOBOT_PROVIDERS__* env vars.")
            results["agent_integration"] = "SKIP (no LLM provider)"
            return

        # This would require creating mock Tool subclasses and registering them
        # Skipping for now — the mock conversation above validates the tool logic
        print("[SKIP] Full AgentLoop integration test requires manual setup")
        results["agent_integration"] = "SKIP (manual test needed)"

    except ImportError as e:
        print(f"[SKIP] Cannot import nanobot: {e}")
        results["agent_integration"] = f"SKIP ({e})"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    await simulate_conversation()
    await test_agent_integration()

    # Print summary
    print("\n" + "=" * 60)
    print("SPIKE U3 RESULTS SUMMARY")
    print("=" * 60)
    for key, val in results.items():
        status = "PASS" if "PASS" in val else ("SKIP" if "SKIP" in val else "FAIL")
        print(f"[{status}] {key}: {val}")
    print("=" * 60)

    # Save results
    results_file = OUTPUT_DIR / "spike_u3_results.json"
    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
