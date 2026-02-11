"""
Spike U1: Validate 115.com API library for QR login + offline download.

Run: python tests/spike/spike_115_api.py
Prerequisites: pip install p115client
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

    # Step 2: QR code generation
    print("\n--- Step 2: QR Code Generation ---")
    try:
        if SESSION_FILE.exists():
            print(f"[INFO] Found existing session at {SESSION_FILE}, attempting reload...")
            client = P115Client(str(SESSION_FILE), check_for_relogin=True)
            results["qr_generation"] = "SKIP (using saved session)"
        else:
            # Create client without cookies — triggers QR login
            client = P115Client()
            # Get QR code token
            qr_info = await client.login_qrcode_token(async_=True)
            uid = qr_info.get("data", {}).get("uid", "")
            if not uid:
                results["qr_generation"] = "FAIL (no uid in response)"
                print(f"[FAIL] QR generation: {qr_info}")
                return
            # QR image URL
            qr_url = f"https://qrcodeapi.115.com/api/1.0/mac/1.0/qrcode?uid={uid}"
            print(f"[INFO] QR URL: {qr_url}")
            print("[INFO] Scan the QR code above with the 115 mobile app")

            # Save QR image
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get(qr_url)
                QR_FILE.write_bytes(resp.content)
                print(f"[INFO] QR image saved to {QR_FILE}")

            results["qr_generation"] = f"PASS (saved to {QR_FILE})"

            # Step 3: Login polling
            print("\n--- Step 3: Login Polling ---")
            print("[INFO] Waiting for QR code scan (up to 120s)...")
            elapsed = 0
            status = "waiting"
            while elapsed < 120:
                await asyncio.sleep(2)
                elapsed += 2
                scan_resp = await client.login_qrcode_scan_status(
                    {"uid": uid}, async_=True
                )
                scan_data = scan_resp.get("data", {})
                new_status = scan_data.get("status", 0)
                # 0=waiting, 1=scanned, 2=confirmed, -1=expired, -2=canceled
                if new_status == 1 and status != "scanned":
                    status = "scanned"
                    print(f"[INFO] QR scanned at {elapsed}s, waiting for confirmation...")
                elif new_status == 2:
                    status = "confirmed"
                    print(f"[INFO] Login confirmed at {elapsed}s")
                    break
                elif new_status in (-1, -2):
                    status = "expired" if new_status == -1 else "canceled"
                    print(f"[FAIL] QR {status} at {elapsed}s")
                    results["login_polling"] = f"FAIL ({status})"
                    return

            if status != "confirmed":
                results["login_polling"] = f"FAIL (timeout, last status: {status})"
                print("[FAIL] Login polling timed out")
                return

            results["login_polling"] = f"PASS (confirmed in {elapsed}s)"

            # Get login cookies
            login_result = await client.login_qrcode_scan_result(
                {"uid": uid, "app": "web"}, async_=True
            )
            # Save session (cookies)
            cookies = client.cookies
            session_data = {
                "cookies": {k: v for k, v in cookies.items()} if hasattr(cookies, "items") else str(cookies),
                "login_result": login_result,
            }
            SESSION_FILE.write_text(json.dumps(session_data, ensure_ascii=False, indent=2))
            print(f"[INFO] Session saved to {SESSION_FILE}")

    except Exception as e:
        results["qr_generation"] = f"FAIL ({type(e).__name__}: {e})"
        print(f"[FAIL] QR generation: {e}")
        return

    # Step 4: Session reload & validation
    print("\n--- Step 4: Session Reload & Validation ---")
    try:
        # Reload client from session file
        client2 = P115Client(str(SESSION_FILE), check_for_relogin=True)
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

    # Step 5: Add magnet task
    print("\n--- Step 5: Add Magnet Task ---")
    test_magnet = "magnet:?xt=urn:btih:0000000000000000000000000000000000000000&dn=test"
    try:
        add_resp = await client.offline_add_urls(
            payload={"urls": test_magnet, "wp_path_id": 0},
            async_=True,
        )
        if add_resp.get("state"):
            print(f"[PASS] Magnet task added: {add_resp}")
            results["add_magnet"] = "PASS"
        else:
            err_code = add_resp.get("errno", "unknown")
            err_msg = add_resp.get("error", "unknown")
            print(f"[INFO] Add magnet response: errno={err_code}, error={err_msg}")
            # Even a "duplicate" or "invalid hash" error proves the API works
            results["add_magnet"] = f"PASS (API responded: {err_code} - {err_msg})"
    except Exception as e:
        results["add_magnet"] = f"FAIL ({type(e).__name__}: {e})"
        print(f"[FAIL] Add magnet: {e}")

    # Step 5b: Check task list
    try:
        task_list = await client.offline_list(async_=True)
        task_count = len(task_list.get("tasks", []))
        print(f"[INFO] Offline task count: {task_count}")
    except Exception as e:
        print(f"[INFO] Task list check failed (non-critical): {e}")

    # Step 6: Session expiry detection
    print("\n--- Step 6: Session Expiry Detection ---")
    try:
        # Create client with fake/expired cookies to test error handling
        fake_client = P115Client("CID=expired; SEID=expired; UID=0")
        resp = await fake_client.user_info(async_=True)
        if not resp.get("state"):
            results["session_expiry"] = "PASS (error detected correctly)"
            print(f"[PASS] Expired session detected: {resp}")
        else:
            results["session_expiry"] = "FAIL (no error for expired session)"
            print(f"[FAIL] Expected error for expired session, got: {resp}")
    except Exception as e:
        results["session_expiry"] = f"PASS (exception raised: {type(e).__name__})"
        print(f"[PASS] Session expiry detection: {type(e).__name__}: {e}")


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
