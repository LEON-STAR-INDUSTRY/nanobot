# DOCUMENT METADATA
title: Film Download - Quick Start Guide
filename: QUICK_START.md
status: Approved
version: 1.2.0
owner: AI Assistant
last_updated: 2026-02-19
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-16 | Claude | Initial creation       |
| 1.1.0   | 2026-02-16 | Claude | Update import paths after integration refactoring |
| 1.2.0   | 2026-02-19 | Claude | Remove hardcoded provider/model; template only contains integration-specific config |

## Purpose & Scope
> 快速验证影片搜索下载功能模块的端到端指南。

---

## 前置条件

- Python 3.11+，已安装 nanobot (`pip install -e ".[dev]"`)
- Playwright 浏览器已安装 (`playwright install chromium`)
- p115client 已安装 (`pip install p115client`)
- nanobot 已完成初始化 (`nanobot onboard`)，`~/.nanobot/config.json` 已存在且 LLM provider 可用
- 飞书应用已创建，具备消息收发权限
- 115 手机 App 可用（用于扫码登录）

## Step 1: 配置 config.json

> **注意：** `docs/02-film_download/config.json` 是完整的配置参考文件（含 agents/providers/channels/integrations 全部段）。`config_template.json` 仅包含影片下载新增的配置片段。

将 `integrations` 和 `channels.feishu` 配置段**合并**到已有的 `~/.nanobot/config.json` 中。完整配置参考 `docs/02-film_download/config.json`。

需要根据自身环境替换的值：

| 配置项 | 说明 | 获取方式 |
|--------|------|----------|
| `agents.defaults.model` | LLM 模型标识 | 根据所用 provider 选择 |
| `providers.*` | LLM provider API key | 对应 provider 平台获取 |
| `channels.feishu.appId` | 飞书应用 App ID | 飞书开放平台 → 应用管理 |
| `channels.feishu.appSecret` | 飞书应用 App Secret | 同上 |

## Step 2: 验证配置加载

```bash
nanobot status
```

预期输出：应显示模型、至少一个 LLM provider API key 状态为 ✓。没有报错即可。

进一步确认 integrations 和 provider 已生效：

```bash
python -c "
from nanobot.config import load_config
c = load_config()
print(f'model: {c.agents.defaults.model}')
p = c.get_provider()
print(f'provider resolved: {p is not None}')
print(f'api_base: {c.get_api_base()}')
print(f'cloud115 enabled: {c.integrations.cloud115.enabled}')
print(f'gying enabled: {c.integrations.gying.enabled}')
print(f'feishu enabled: {c.channels.feishu.enabled}')
"
```

- `provider resolved` 应为 `True`（如果为 `False`，检查 providers 配置）
- 三项 `enabled` 都应为 `True`

## Step 3: 验证 gying.org 抓取

gying.org 需要登录才能使用。首次运行必须使用 `browser_data_dir` 持久化 cookies，并在浏览器中手动完成登录。

**Step 3a: 首次登录（仅需一次）**

```bash
python -c "
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BROWSER_DIR = str(Path.home() / '.nanobot' / 'browser_data' / 'gying')

async def login():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch_persistent_context(
        BROWSER_DIR,
        headless=False,
        locale='zh-CN',
        viewport={'width': 1280, 'height': 800},
    )
    page = browser.pages[0] if browser.pages else await browser.new_page()
    await page.goto('https://www.gying.org/')
    print('请在浏览器中完成登录，登录成功后按回车继续...')
    input()
    await browser.close()
    await pw.stop()
    print('登录 cookies 已保存到', BROWSER_DIR)

asyncio.run(login())
"
```

> 登录完成后 cookies 会保存在 `~/.nanobot/browser_data/gying/` 目录中，后续运行自动复用。

**Step 3b: 验证搜索功能**

```bash
python -c "
import asyncio
from pathlib import Path
from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

BROWSER_DIR = str(Path.home() / '.nanobot' / 'browser_data' / 'gying')

async def test():
    tool = GyingScraperTool(
        browser_data_dir=BROWSER_DIR,
        headless=False,
    )
    result = await tool.execute(action='search', query='沙丘')
    print(result)
    await tool.close()

asyncio.run(test())
"
```

**预期结果：**
- 浏览器窗口弹出，自动使用已保存的登录状态
- 搜索"沙丘"
- 返回 JSON 格式的搜索结果列表
- 每条结果包含 `title`、`url`、`rating`

**常见问题：**
- 如果提示"gying.org 未登录"：重新执行 Step 3a 完成登录
- 如果浏览器启动失败：运行 `playwright install chromium`
- 如果被反爬：安装 `pip install playwright-stealth`

## Step 4: 验证 115 登录

```bash
python -c "
import asyncio
from pathlib import Path
from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool

SESSION_PATH = str(Path.home() / '.nanobot' / 'cloud115_session.json')

async def test():
    tool = Cloud115Tool(session_path=SESSION_PATH)

    # 登录：终端会显示二维码，用115 App扫码
    result = await tool.execute(action='login')
    print(result)

    # 验证 session
    result = await tool.execute(action='check_session')
    print(result)

asyncio.run(test())
"
```

**预期结果：**
- 终端显示二维码，使用 115 手机 App 扫码
- 扫码确认后自动完成登录，输出 `{"logged_in": true, "message": "115 登录成功"}`
- `~/.nanobot/cloud115_session.json` 文件已创建

## Step 5: 验证飞书通道

启动 gateway：

```bash
nanobot gateway
```

在飞书中给 bot 发送：**帮我找 星际穿越**

**预期交互流程：**

```
你: 帮我找 星际穿越
Bot: 搜索结果：
     1. 星际穿越 Interstellar (2014) 9.4
     2. ...
     请回复序号查看详情

你: 1
Bot: 星际穿越 (2014)
     豆瓣: 9.4 | IMDb: 8.7
     类型: 科幻/冒险/剧情
     ...
     是否需要下载？回复 '4K' 或 '1080P'

你: 4K
Bot: 找到以下 4K 中字资源：
     1. 星际穿越.4K.中英字幕.mkv (45.2 GB)
     2. ...
     请回复序号选择下载

你: 1
Bot: (如果未登录115) 请扫描二维码登录115
     [二维码图片]
     扫码后回复 '已扫码'

你: 已扫码
Bot: 登录成功！已添加离线下载任务: 星际穿越.4K.中英字幕.mkv
```

## Step 6: 验证定时任务（Scenario B）

在飞书中发送：**每天早上9点帮我检查新片**

Bot 应创建 cron 任务。验证：

```bash
nanobot cron list
```

应显示一条 `gying-daily-check` 任务，schedule 为 `0 9 * * *`。

手动触发测试：

```bash
nanobot cron run <job_id> --force
```

## Step 7: 验证已看记录

运行 Step 6 后，检查文件：

```bash
cat ~/.nanobot/workspace/film_download/seen_movies.json
```

应包含本次检查到的影片记录。

## 问题排查清单

| 问题 | 排查方向 |
|------|----------|
| LLM 调用失败 (AuthenticationError) | 运行 `nanobot status` 确认 provider API key 状态为 ✓；确保 config.json 中 `agents.defaults.model` 与 `providers` 中配置的 key 匹配 |
| `gying_search` 工具未注册 | 检查 config.json 中 `integrations.gying.enabled` 是否为 `true` |
| `cloud115` 工具未注册 | 检查 config.json 中 `integrations.cloud115.enabled` 是否为 `true` |
| 飞书收不到消息 | 检查 `channels.feishu.enabled`、appId/appSecret 是否正确 |
| 搜索返回空结果 | gying.org 可能改版，检查 CSS selectors 是否仍有效 |
| 115 登录失败 | 检查网络是否能访问 115.com API |
| 定时任务不触发 | 确认 gateway 进程持续运行，检查 `nanobot cron list` |
| 已看记录不更新 | 检查 `~/.nanobot/workspace/film_download/` 目录权限 |

## 全部测试通过后

```bash
# 运行完整测试套件确认无回归
pytest -v

# 当前应有 75 tests, all passing
```
