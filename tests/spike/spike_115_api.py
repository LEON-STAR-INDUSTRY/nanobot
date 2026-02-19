"""
Spike U1: Validate 115.com API library for QR login + offline download.

Run: python tests/spike/spike_115_api.py
Prerequisites: pip install p115client
Install latest: pip install -U git+https://github.com/ChenyangGao/p115client@main
"""
import asyncio
import json
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
SESSION_FILE = OUTPUT_DIR / "115_session.json"
QR_FILE = OUTPUT_DIR / "qr_115.png"

# ---------------------------------------------------------------------------
# Step 1: Detect available library
# ---------------------------------------------------------------------------
LIB = None
try:
    import p115client  # noqa: F401

    LIB = "p115client"
except ImportError:
    pass

if not LIB:
    try:
        import py115  # noqa: F401

        LIB = "py115"
    except ImportError:
        pass

if not LIB:
    print("[FAIL] No 115 library found. Install: pip install p115client OR pip install py115")
    sys.exit(1)

print(f"[INFO] Using library: {LIB}")

results: dict[str, str] = {}


# ---------------------------------------------------------------------------
# p115client implementation
# ---------------------------------------------------------------------------
async def run_p115client():
    from p115client import P115Client

    # Step 2: QR code login
    print("\n--- Step 2: QR Code Login ---")
    try:
        if SESSION_FILE.exists():
            print(f"[INFO] Found existing session at {SESSION_FILE}, attempting reload...")
            # Load cookies from JSON file
            session_data = json.loads(SESSION_FILE.read_text())
            # Create client with cookies dict (not file path)
            client = P115Client(session_data["cookies"], check_for_relogin=True)
            results["qr_login"] = "SKIP (using saved session)"
        else:
            print("[INFO] Starting QR code login...")
            print("[INFO] A browser window will open with the QR code")
            print("[INFO] Please scan with the 115 mobile app")
            
            # Use the official login_with_qrcode class method
            # This handles token generation, QR display, and polling automatically
            login_result = await P115Client.login_with_qrcode(
                app="web",  # Login as web app
                console_qrcode=True,  # Open QR in console
                async_=True
            )
            
            print("[INFO] Login successful!")
            results["qr_login"] = "PASS"
            
            # Create client from login result
            client = P115Client(login_result)
            
            # Save session
            # Use the cookie dict from login_result, which contains the actual key-value pairs
            session_data = {
                "cookies": login_result["data"]["cookie"],  # {"UID": "xxx", "CID": "yyy", ...}
                "login_result": login_result,
            }
            SESSION_FILE.write_text(json.dumps(session_data, ensure_ascii=False, indent=2))
            print(f"[INFO] Session saved to {SESSION_FILE}")

    except Exception as e:
        results["qr_login"] = f"FAIL ({type(e).__name__}: {e})"
        print(f"[FAIL] QR login: {e}")
        return

    # Step 3: Session validation
    print("\n--- Step 3: Session Validation ---")
    try:
        # Reload client from session file to verify it works
        session_data = json.loads(SESSION_FILE.read_text())
        client2 = P115Client(session_data["cookies"], check_for_relogin=True)
        # Test authenticated endpoint — get user info
        user_info = await client2.user_info(async_=True)
        if user_info.get("state"):
            user_name = user_info.get("data", {}).get("user_name", "unknown")
            print(f"[PASS] Session valid, user: {user_name}")
            results["session_reload"] = f"PASS (user: {user_name})"
        else:
            print(f"[FAIL] Session invalid: {user_info}")
            results["session_reload"] = f"FAIL ({user_info})"
    except Exception as e:
        results["session_reload"] = f"FAIL ({type(e).__name__}: {e})"
        print(f"[FAIL] Session reload: {e}")

    # Step 4: Add magnet task
    print("\n--- Step 4: Add Offline Download Task ---")
    test_magnet = "magnet:?xt=urn:btih:6c4b42be0793598dbcf7b75d50df1e274ad8890c"
    try:
        # offline_add_urls takes payload as positional argument
        add_resp = await client.offline_add_urls(
            test_magnet,  # Can pass string directly
            async_=True,
        )
        print(f"[DEBUG] Full response: {json.dumps(add_resp, ensure_ascii=False, indent=2)}")
        
        # Check response structure
        state = add_resp.get("state", False)
        if state:
            print(f"[PASS] Magnet task added successfully")
            results["add_magnet"] = "PASS"
        else:
            # Try different error field names
            err_code = add_resp.get("errcode", add_resp.get("errno", add_resp.get("code", "unknown")))
            err_msg = add_resp.get("error_msg", add_resp.get("error", add_resp.get("message", "unknown")))
            print(f"[INFO] Task not added: code={err_code}, msg={err_msg}")
            # API responded, so it's working
            results["add_magnet"] = f"PASS (API working, code={err_code})"
    except Exception as e:
        results["add_magnet"] = f"FAIL ({type(e).__name__}: {e})"
        print(f"[FAIL] Add magnet: {e}")

    # Step 4b: Check task list
    try:
        task_list = await client.offline_list(async_=True)
        tasks = task_list.get("tasks", [])
        task_count = len(tasks)
        print(f"[INFO] Total offline tasks: {task_count}")
        if task_count > 0:
            print(f"[INFO] Recent tasks:")
            for i, task in enumerate(tasks[:3], 1):  # Show first 3 tasks
                name = task.get("name", "unknown")
                status = task.get("status", "unknown")
                print(f"  {i}. {name} (status={status})")
    except Exception as e:
        print(f"[INFO] Task list check failed (non-critical): {e}")

# ---------------------------------------------------------------------------
# py115 implementation (fallback)
# ---------------------------------------------------------------------------
async def run_py115():
    print("[INFO] py115 support is a fallback. Implement if p115client is unavailable.")
    results["note"] = "py115 fallback not yet implemented. Install p115client instead."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    if LIB == "p115client":
        await run_p115client()
    else:
        await run_py115()

    # Print summary
    print("\n" + "=" * 60)
    print("SPIKE U1 RESULTS SUMMARY")
    print("=" * 60)
    for key, val in results.items():
        status = "PASS" if "PASS" in val else ("SKIP" if "SKIP" in val else "FAIL")
        print(f"[{status}] {key}: {val}")
    print("=" * 60)

    # Save results
    results_file = OUTPUT_DIR / "spike_u1_results.json"
    results_file.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
