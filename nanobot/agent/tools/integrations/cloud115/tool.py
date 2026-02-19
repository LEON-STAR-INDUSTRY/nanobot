"""Cloud115Tool: 115.com QR login + offline magnet download."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


class Cloud115Tool(Tool):
    """Tool for interacting with 115.com cloud storage via p115client."""

    def __init__(
        self,
        session_path: str = "",
        default_save_path: str = "/",
    ):
        self._session_path = Path(session_path) if session_path else None
        self._default_save_path = default_save_path
        self._client = None

    @property
    def name(self) -> str:
        return "cloud115"

    @property
    def description(self) -> str:
        return (
            "Interact with 115.com cloud storage. Actions: "
            "login (generate QR code for scanning), "
            "check_session (verify login status or confirm pending QR scan), "
            "add_magnet (add magnet link to offline download), "
            "task_status (check offline download task list)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["login", "check_session", "add_magnet", "task_status"],
                    "description": "Action to perform.",
                },
                "magnet_url": {
                    "type": "string",
                    "description": "Magnet link URL (required for add_magnet).",
                },
                "save_path": {
                    "type": "string",
                    "description": "115 folder path to save downloads (optional).",
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        try:
            if action == "login":
                return await self._do_login()
            elif action == "check_session":
                return await self._do_check_session()
            elif action == "add_magnet":
                return await self._do_add_magnet(
                    kwargs.get("magnet_url", ""),
                    kwargs.get("save_path", ""),
                )
            elif action == "task_status":
                return await self._do_task_status()
            else:
                return json.dumps({"error": f"未知操作: {action}"})
        except Exception as e:
            logger.error(f"Cloud115Tool error: {e}")
            return json.dumps({"error": f"115操作失败: {type(e).__name__}: {e}"})

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _do_login(self) -> str:
        from p115client import P115Client

        login_result = await P115Client.login_with_qrcode(
            app="web",
            console_qrcode=True,
            async_=True,
        )
        cookies = login_result.get("data", {}).get("cookie", {})
        await self._save_session(cookies)
        self._client = P115Client(login_result)
        return json.dumps({
            "logged_in": True,
            "message": "115 登录成功",
        }, ensure_ascii=False)

    async def _do_check_session(self) -> str:
        # Try existing in-memory client
        if self._client:
            try:
                info = await self._validate_client(self._client)
                if info:
                    return json.dumps({"logged_in": True, "user": info}, ensure_ascii=False)
            except Exception:
                self._client = None

        if self._session_path and self._session_path.exists():
            try:
                session_data = json.loads(self._session_path.read_text())
                cookies = session_data.get("cookies", {})
                self._client = await self._create_client(cookies)
                info = await self._validate_client(self._client)
                if info:
                    return json.dumps({"logged_in": True, "user": info}, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Session reload failed: {e}")
                self._client = None

        return json.dumps({
            "logged_in": False,
            "message": "未登录115，请发送'登录115'开始扫码登录。",
        }, ensure_ascii=False)

    async def _do_add_magnet(self, magnet_url: str, save_path: str) -> str:
        if not magnet_url:
            return json.dumps({"error": "缺少magnet_url参数"}, ensure_ascii=False)

        if not self._client:
            # Try session reload
            await self._do_check_session()
            if not self._client:
                return json.dumps({
                    "error": "未登录115，请先扫码登录。",
                    "logged_in": False,
                }, ensure_ascii=False)

        resp = await self._client.offline_add_urls(magnet_url, async_=True)
        state = resp.get("state", False)
        if state:
            tasks = resp.get("tasks", [])
            task_names = [t.get("name", "unknown") for t in tasks]
            return json.dumps({
                "success": True,
                "message": "离线下载任务已添加",
                "tasks": task_names,
            }, ensure_ascii=False)
        else:
            err_code = resp.get("errcode", resp.get("errno", "unknown"))
            err_msg = resp.get("error_msg", resp.get("error", "unknown"))
            # Detect session expiry (common error codes)
            if err_code in (911, 40101, 40100, 990001):
                self._client = None
                return json.dumps({
                    "success": False,
                    "error": "115 登录已过期，请发送 '登录115' 重新扫码登录。",
                    "logged_in": False,
                }, ensure_ascii=False)
            return json.dumps({
                "success": False,
                "error": f"添加失败: {err_code} - {err_msg}",
            }, ensure_ascii=False)

    async def _do_task_status(self) -> str:
        if not self._client:
            await self._do_check_session()
            if not self._client:
                return json.dumps({
                    "error": "未登录115，请先扫码登录。",
                }, ensure_ascii=False)

        resp = await self._client.offline_list(async_=True)
        raw_tasks = resp.get("tasks", [])
        tasks = []
        for t in raw_tasks[:10]:
            tasks.append({
                "name": t.get("name", "unknown"),
                "status": t.get("status", -1),
                "percent_done": t.get("percent_done", 0),
                "size": t.get("size", 0),
            })
        return json.dumps({"tasks": tasks}, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _create_client(self, cookies: dict):
        """Create P115Client from cookies dict."""
        from p115client import P115Client

        return P115Client(cookies, check_for_relogin=True)

    async def _validate_client(self, client) -> str | None:
        """Validate client session. Returns user name or None."""
        try:
            resp = await client.user_info(async_=True)
            if resp.get("state"):
                return resp.get("data", {}).get("user_name", "unknown")
        except Exception:
            pass
        return None

    async def _save_session(self, cookies: dict) -> None:
        """Save session cookies to file."""
        if not self._session_path:
            return
        self._session_path.parent.mkdir(parents=True, exist_ok=True)
        session_data = {"cookies": cookies}
        self._session_path.write_text(json.dumps(session_data, ensure_ascii=False, indent=2))
        logger.info(f"115 session saved to {self._session_path}")


# ---------------------------------------------------------------------------
# TOOLS descriptor -- used by IntegrationLoader to auto-register tools
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "class": Cloud115Tool,
        "config_map": {
            "session_path": "session_path",
            "default_save_path": "default_save_path",
        },
    },
]
