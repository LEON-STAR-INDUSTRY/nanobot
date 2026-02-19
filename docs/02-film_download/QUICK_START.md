# DOCUMENT METADATA
title: Film Download - Quick Start Guide
filename: QUICK_START.md
status: Approved
version: 1.1.0
owner: AI Assistant
last_updated: 2026-02-16
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-16 | Claude | Initial creation       |
| 1.1.0   | 2026-02-16 | Claude | Update import paths after integration refactoring |

## Purpose & Scope
> 快速验证影片搜索下载功能模块的端到端指南。

---

## 前置条件

- Python 3.11+，已安装 nanobot (`pip install -e ".[dev]"`)
- Playwright 浏览器已安装 (`playwright install chromium`)
- p115client 已安装 (`pip install p115client`)
- 飞书应用已创建，具备消息收发权限
- 115 手机 App 可用（用于扫码登录）

## Step 1: 配置 config.json

将 `docs/02-film_download/config_template.json` 复制到 `~/.nanobot/config.json`，替换占位符：

```bash
cp docs/02-film_download/config_template.json ~/.nanobot/config.json
```

需要替换的值：

| 占位符 | 说明 | 获取方式 |
|--------|------|----------|
| `<YOUR_ANTHROPIC_API_KEY>` | Anthropic API Key | https://console.anthropic.com |
| `<YOUR_FEISHU_APP_ID>` | 飞书应用 App ID | 飞书开放平台 → 应用管理 |
| `<YOUR_FEISHU_APP_SECRET>` | 飞书应用 App Secret | 同上 |
| `<YOUR_FEISHU_OPEN_ID>` | 你的飞书 Open ID | 飞书 API 调试台获取 |

## Step 2: 验证配置加载

```bash
nanobot status
```

预期输出：应显示模型、API key 状态。没有报错即可。

进一步确认 integrations 已生效：

```bash
python -c "
from nanobot.config import load_config
c = load_config()
print(f'cloud115 enabled: {c.integrations.cloud115.enabled}')
print(f'gying enabled: {c.integrations.gying.enabled}')
print(f'feishu enabled: {c.channels.feishu.enabled}')
"
```

三项都应为 `True`。

## Step 3: 验证 gying.org 抓取

用 `headless: false` 测试浏览器能否正常工作（临时修改 config 或直接用脚本）：

```bash
python -c "
import asyncio
from nanobot.agent.tools.integrations.gying.tool import GyingScraperTool

async def test():
    tool = GyingScraperTool(headless=False)
    result = await tool.execute(action='search', query='沙丘')
    print(result)
    await tool.close()

asyncio.run(test())
"
```

**预期结果：**
- 浏览器窗口弹出，访问 gying.org
- 搜索"沙丘"
- 返回 JSON 格式的搜索结果列表
- 每条结果包含 `title`、`url`、`rating`

**常见问题：**
- 如果搜索框找不到：检查 gying.org 是否改版
- 如果浏览器启动失败：运行 `playwright install chromium`
- 如果被反爬：安装 `pip install playwright-stealth`

## Step 4: 验证 115 登录

```bash
python -c "
import asyncio
from nanobot.agent.tools.integrations.cloud115.tool import Cloud115Tool

async def test():
    tool = Cloud115Tool(session_path='$HOME/.nanobot/cloud115_session.json')

    # Step 1: 生成二维码
    result = await tool.execute(action='login')
    print(result[:200])
    print('... 请用115 App扫描二维码 ...')

    # Step 2: 等待你扫码后，运行检查
    input('扫码完成后按回车继续...')
    result = await tool.execute(action='check_session')
    print(result)

asyncio.run(test())
"
```

**预期结果：**
- 返回包含 `qr_image_base64` 的 JSON
- 扫码后 `check_session` 返回 `{"logged_in": true}`
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
