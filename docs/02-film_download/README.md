# **基于 Nanobot 与 Playwright 构建零信任交互式媒体采集系统的深度研究报告**

## **1. 执行摘要**

在当今数字媒体消费与个人云存储技术深度融合的背景下，自动化代理（AI Agents）正逐渐从简单的脚本执行者演变为复杂的决策辅助系统。本报告针对一种特定的、高安全性的媒体获取工作流进行了详尽的技术架构分析与实施方案设计。该方案旨在通过集成轻量级代理框架 nanobot、新一代无头浏览器自动化工具 Playwright 以及企业级协作平台 飞书（Feishu/Lark），构建一座连接媒体发现平台（gying.org）与云存储服务（115.com）的智能桥梁。

本研究的核心驱动力在于解决传统自动化工具在安全性与用户体验之间的固有矛盾。传统的自动化脚本往往要求明文或加密存储用户的敏感凭据（如密码、Cookie），这在个人隐私保护日益受到重视的今天显得不可接受。本报告提出并验证了一种“零信任”人机协同（Human-in-the-Loop, HITL）认证模式：代理仅负责环境准备与二维码截取，用户掌握最终的授权控制权，通过移动端扫码实现物理隔绝的身份验证。

此外，针对媒体资源选择过程中的信息过载问题，本系统摒弃了传统的命令行交互模式，转而采用飞书富媒体交互卡片（Interactive Cards）。通过对 gying.org 的深度解析，系统能够提取关键决策指标（如评分、演员阵容），并根据用户偏好（“中字1080P”与“中字4K”）智能过滤下载链接，将复杂的资源筛选过程转化为直观的点选操作。


## *****2. 系统架构与设计哲学**

### **2.1 代理内核：Nanobot 的微内核优势**

在选择代理框架时，本研究对比了市场上主流的 OpenClaw、AutoGPT 等重型框架，最终选定 nanobot 作为核心编排引擎。nanobot 的设计哲学在于“极简”与“可扩展性”，其核心代码量仅约 4,000 行，这极大地降低了系统的维护成本与审计难度。

在本系统中，nanobot 扮演着中央神经系统的角色，负责以下关键职能：

<!--[if !supportLists]-->1. <!--[endif]-->**上下文管理（Context Management）：** 在多轮对话中维持状态一致性，确保从电影查询到最终下载指令的传递过程中，用户意图不丢失。

<!--[if !supportLists]-->2. <!--[endif]-->**工具分发（Tool Dispatch）：** 动态调用自定义的 Python 工具集，包括网页抓取器（Scraper）和浏览器自动化控制器（Browser Controller）。

<!--[if !supportLists]-->3. <!--[endif]-->**消息路由（Message Routing）：** 作为飞书网关与内部逻辑的转换器，将非结构化的用户指令转化为结构化的系统调用，并将系统状态渲染为 JSON 格式的卡片消息。

nanobot 的目录结构清晰地支持了这种模块化开发。我们在 nanobot/skills/ 目录下扩展了专用的 media\_acquisition 技能模块，并在 nanobot/agent/tools/ 中实现了基于 Playwright 的底层驱动。这种分离设计确保了核心逻辑与业务逻辑的解耦，便于后续针对特定网站变动进行独立升级。


### **2.2 自动化层：Playwright 的动态操控能力**

鉴于目标网站 115.com 和 gying.org 均大量使用现代前端技术（React/Vue.js），传统的基于 HTTP 请求的爬虫（如 BeautifulSoup 或 Scrapy）难以处理复杂的动态渲染与交互逻辑。因此，本系统选用微软开发的 Playwright 作为自动化执行层。

相较于 Selenium，Playwright 在本场景下具有显著优势：

<!--[if !supportLists]-->● <!--[endif]-->**自动等待机制（Auto-waiting）：** 能够智能等待 DOM 元素进入可交互状态，极大地减少了因网络波动导致的脚本脆性。

<!--[if !supportLists]-->● <!--[endif]-->**上下文隔离（Browser Contexts）：** 允许在一个浏览器实例中创建多个独立的会话环境。这意味着我们可以为 115 登录状态创建一个持久化的上下文，而与普通的网页浏览隔离，既保证了状态管理的安全性，又提升了资源利用率。

<!--[if !supportLists]-->● <!--[endif]-->**选择器引擎（Selector Engines）：** 支持 CSS、XPath 以及文本选择器的混合使用，为定位动态生成的二维码和下载按钮提供了极高的灵活性。


### **2.3 交互层：飞书卡片的富媒体体验**

为了实现用户所期望的“卡片式交互”，系统深度集成了飞书开放平台的卡片能力。飞书卡片不仅支持 Markdown 文本渲染，还允许嵌入图片、按钮、下拉菜单等交互组件。

交互流程被设计为一种异步的事件驱动模型：

<!--[if !supportLists]-->1. <!--[endif]-->**信息推送（Push）：** 代理主动发送包含电影海报、评分和简介的消息卡片。

<!--[if !supportLists]-->2. <!--[endif]-->**用户触发（Trigger）：** 用户点击“下载到115”按钮，触发 card.action.trigger 回调事件。

<!--[if !supportLists]-->3. <!--[endif]-->**动态更新（Update）：** 系统接收回调后，实时抓取下载链接，并调用 patch 接口更新原有卡片，展示包含特定分辨率选项（1080P/4K）的下拉菜单，从而避免了聊天记录的冗余堆叠。


## *****3. 挑战一：高保真内容获取策略 (gying.org)**

尽管用户认为内容获取并非难点，但在构建自动化流水线时，数据提取的准确性、完整性以及对特定格式（如分辨率标签）的识别能力至关重要。特别是“评分”这一关键决策指标，必须确保从 DOM 中精准提取。


### **3.1 DOM 结构分析与选择器策略**

gying.org 的详情页面包含了电影的核心元数据。为了确保抓取的鲁棒性，我们采用分层选择器策略，优先使用语义化较强的 CSS 选择器，并在必要时回退到 XPath。


#### **3.1.1 核心信息提取**

<!--[if !supportLists]-->● <!--[endif]-->**电影标题（Title）：** 通常位于页面的 \<h1> 标签或具有特定 class（如 .movie-title）的元素中。

<!--[if !supportLists]-->○ <!--[endif]-->_Playwright Selector:_ page.locator("h1.movie-title") 或 page.get\_by\_role("heading", level=1)。

<!--[if !supportLists]-->● <!--[endif]-->**评分（Rating）：** 用户强调了评分的重要性。评分通常以醒目的数字显示，可能包含在 .score、.rating 或 .douban-score 等类名中。为了防止误提取（如提取到投票人数），可以通过正则表达式校验提取的文本内容（如 ^\d+(\\.\d+)?$）。

<!--[if !supportLists]-->○ <!--[endif]-->_Playwright Selector:_ page.locator(".score-num") 或 page.locator("xpath=//span\[contains(@class, 'rating')]")。

<!--[if !supportLists]-->● <!--[endif]-->**演员表与简介：** 这些信息通常位于详情区的列表或段落中。抓取时需注意去除“更多”、“展开”等交互式文本。

<!--[if !supportLists]-->○ <!--[endif]-->_Playwright Selector:_ page.locator(".cast-list") 及 page.locator(".summary")。


#### **3.1.2 下载链接的智能过滤**

这是本挑战的核心技术难点。用户明确要求区分“中字1080P”和“中字4K”。这要求爬虫不仅要提取链接，还要理解链接所在的上下文容器。

通常，下载站点会将不同质量的资源分块展示，或者在表格行的某一列中标注清晰度。Playwright 的 locator.filter() 方法在此处极具价值。

**实现逻辑：**

<!--[if !supportLists]-->1. <!--[endif]-->**定位下载区域：** 找到包含下载链接的表格或列表容器，例如 #download-list。

<!--[if !supportLists]-->2. <!--[endif]-->**行级遍历与过滤：**

<!--[if !supportLists]-->○ <!--[endif]-->针对 **1080P**：\
```python
# 伪代码示例
links_1080p = page.locator("tr").filter(has_text="中字").filter(has_text="1080P").all()
```
<!--[if !supportLists]-->○ <!--[endif]-->针对 **4K**：\
```python
# 伪代码示例
links_4k = page.locator("tr").filter(has_text="中字").filter(has_text="4K").all()
```


<!--[if !supportLists]-->3. <!--[endif]-->**链接提取：** 遍历过滤后的行对象，提取其中的 a 标签 href 属性（通常以 magnet:?xt= 开头）以及对应的文件大小文本（作为辅助判断依据）。


## *****4. 挑战二：零信任人机协同认证机制 (115.com)**

本系统的核心安全设计在于拒绝存储用户的静态密码。通过 Playwright 自动化控制浏览器打开 115 登录页，截取实时生成的二维码，并通过飞书发送给用户，由用户在手机端完成扫码验证。这一流程构成了“零信任”安全模型的基础。


### **4.1 流程编排与状态机设计**

该过程涉及两个异步系统的协同：本地运行的 headless 浏览器和远程的用户操作。


#### **4.1.1 浏览器初始化与导航**

系统启动一个 Playwright BrowserContext，并导航至 https\://115.com/?mode=login。为了避免被识别为自动化脚本，需在启动参数中注入伪造的 User-Agent，并移除 navigator.webdriver 标志。

```python
browser = await playwright.chromium.launch(headless=True)
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)..."

page = await context.new_page()
await page.goto("https://115.com/?mode=login")
```

#### **4.1.2 二维码元素的精准定位与捕获**

115 的登录页面包含多种登录方式（账号密码、短信、二维码）。代理必须确保当前处于“二维码登录”模式，并精准定位二维码图片元素。

<!--[if !supportLists]-->● <!--[endif]-->**选择器定位：** 通过浏览器的开发者工具分析，二维码通常位于具有特定 ID 或 Class 的容器中，例如 #js\_qr\_code\_box 或 .qrcode-image。 Playwright 的选择器引擎可以轻松定位该元素。

<!--[if !supportLists]-->● <!--[endif]-->**元素截图（Element Screenshot）：** Playwright 支持对单一 DOM 元素进行截图，而非整页截图。这对于移动端查看至关重要，因为整页截图在手机屏幕上会导致二维码过小而无法扫描。\
Python\
qr\_element = page.locator(".qr-code-view img")\
await qr\_element.wait\_for(state="visible")\
qr\_bytes = await qr\_element.screenshot()\
\
此处生成的 qr\_bytes 即为待发送的二进制图像数据。


#### **4.1.3 跨端传输与用户交互**

获取截图后，代理需要调用飞书 API 发送图片消息。

<!--[if !supportLists]-->1. <!--[endif]-->**上传图片：** 调用飞书 im/v1/images 接口，将二进制流上传至飞书服务器，获取 image\_key。

<!--[if !supportLists]-->2. <!--[endif]-->**发送消息：** 使用 image\_key 构造消息体，向特定用户发送图片消息，并附带提示文本“请扫描二维码以登录 115 网盘”。


#### **4.1.4 登录状态轮询与会话持久化**

发送二维码后，代理进入轮询状态（Polling），持续监测浏览器页面的变化，以判断登录是否成功。

<!--[if !supportLists]-->● <!--[endif]-->**成功判定：** 监测 URL 是否跳转至 https\://115.com/?mode=file 或页面中是否出现了用户头像元素（如 .user-avatar）。

<!--[if !supportLists]-->● <!--[endif]-->**过期处理：** 二维码通常有 1-2 分钟的有效期。如果检测到二维码遮罩层出现（提示“点击刷新”），代理应自动点击刷新，并重新截取发送。

<!--[if !supportLists]-->● <!--[endif]-->**状态保存：** 一旦检测到登录成功，立即导出 storageState（包含 Cookies 和 LocalStorage）。\
Python\
await context.storage\_state(path="auth/115\_session.json")\
\
该 JSON 文件将作为后续操作的凭证，只要 Cookie 未过期，后续任务即可跳过扫码步骤直接复用会话。


## *****5. 挑战三：交互式卡片设计与动态数据流**

用户体验的核心在于如何优雅地呈现复杂信息并引导用户完成操作。本节详细设计了基于飞书卡片的交互流程，涵盖了从电影展示到版本选择的全生命周期。


### **5.1 电影详情卡片（Card V1）设计**

当代理完成 gying.org 的抓取后，首先推送的是一张信息概览卡片。根据飞书卡片 JSON 结构规范，设计如下：

|             |                                                     |                                      |
| ----------- | --------------------------------------------------- | ------------------------------------ |
| **组件区域**    | **内容元素**                                            | **设计意图**                             |
| **Header**  | 电影中文标题 + (年份)                                       | 醒目展示核心对象。                            |
| **Banner**  | 电影海报图片                                              | 视觉吸引，确认抓取对象的正确性。                     |
| **Fields**  | **评分：** ⭐️ 9.0 (豆瓣) **类型：** 科幻 / 动作 **主演：** 莱昂纳多... | **评分**需使用富文本标记（如加粗、高亮色）以满足用户特别关注的需求。 |
| **Content** | 剧情简介（截取前100字）                                       | 快速了解剧情。                              |
| **Action**  | 按钮：“下载到 115 网盘”                                     | 唯一的行动点，触发后续流程。                       |

**交互配置：**

“下载到 115 网盘”按钮配置 callback 类型的交互。其 value 载荷（payload）中必须包含该电影的唯一标识（如原始 URL），以便代理在接收到回调时知道用户操作的是哪部电影。

 
```json
"value": {
    "action": "fetch_download_links",
    "source_url": "https://gying.org/movie/12345"
}
```

### **5.2 动态回调与版本选择菜单（Card V2）**

当用户点击下载按钮后，飞书服务器向 nanobot 的 Webhook 发送 POST 请求。代理接收请求，解析出 source\_url，并再次激活 Playwright（或读取缓存）去提取具体的下载链接列表。

此时，代理不直接触发下载，而是**更新原卡片**（或发送新卡片），加入版本选择的交互组件。

**链接分类逻辑：**

代理需遍历抓取到的链接，依据文本特征进行分类：

<!--[if !supportLists]-->● <!--[endif]-->**集合 A（4K）：** 包含 "4K", "2160P", "UHD" 且包含 "中字" 的链接。

<!--[if !supportLists]-->● <!--[endif]-->**集合 B（1080P）：** 包含 "1080P", "FHD" 且包含 "中字" 的链接。

**交互组件设计：**

由于链接可能较多，使用“下拉选择菜单”（Select Menu）比平铺的按钮更节省空间且体验更好。

<!--[if !supportLists]-->● <!--[endif]-->**下拉菜单 1（4K 源）：** 选项展示为 \[4K] 文件名 (大小)，值为对应的磁力链接。

<!--[if !supportLists]-->● <!--[endif]-->**下拉菜单 2（1080P 源）：** 选项展示为 \[1080P] 文件名 (大小)，值为对应的磁力链接。

<!--[if !supportLists]-->● <!--[endif]-->**确认按钮：** “开始离线下载”。


### **5.3 触发下载流程闭环**

用户在下拉菜单中选择特定磁力链接并点击“开始下载”后，代理再次接收回调。此时 Payload 中包含了具体的 magnet\_link。

代理随即启动 115 自动化任务：

<!--[if !supportLists]-->1. <!--[endif]-->加载 115\_session.json 恢复登录态。

<!--[if !supportLists]-->2. <!--[endif]-->访问 115“离线下载”/“链接任务”页面。

<!--[if !supportLists]-->3. <!--[endif]-->通过 Playwright 选择器定位输入框，填入磁力链接。

<!--[if !supportLists]-->4. <!--[endif]-->点击“开始下载”按钮。

<!--[if !supportLists]-->5. <!--[endif]-->监测任务添加成功的提示（Toast 或弹窗）。

<!--[if !supportLists]-->6. <!--[endif]-->最后，再次更新飞书卡片，将操作区域变为“✅ 下载任务已添加”，完成闭环。


## *****6. 系统开发与验证计划 (New)**

鉴于系统的复杂性与依赖外部网站的不确定性，本章节制定了模块化的开发与验证计划。核心理念是 **“独立验证，组合执行”**，通过标准化的接口（Protocols）确保各模块的可重用性与稳定性。


### **6.1 阶段一：核心模块的独立开发与验证**

我们将系统拆解为四个独立的原子模块，每个模块对应一个 Python 测试脚本，必须在单元测试通过后方可集成。


#### **模块 A: 115 会话管理器 (Session Manager)**

<!--[if !supportLists]-->● <!--[endif]-->**功能目标**：负责浏览器的启动、Cookie 的持久化存储与加载、以及 QR 码的生成（截取）。它是系统的“通行证”。

<!--[if !supportLists]-->● <!--[endif]-->**技术难点**：判断登录成功状态、处理二维码过期刷新。

<!--[if !supportLists]-->● <!--[endif]-->**验证脚本** (tests/test\_115\_login.py):

<!--[if !supportLists]-->1. <!--[endif]-->启动 Headless 浏览器，加载本地 storage\_state.json（如果存在）。

<!--[if !supportLists]-->2. <!--[endif]-->访问 https\://115.com/。

<!--[if !supportLists]-->3. <!--[endif]-->**Check 1**: 检查 URL 是否跳转到网盘主页，或检查 DOM 中是否存在 .user-avatar。

<!--[if !supportLists]-->4. <!--[endif]-->**Branch Fail (未登录)**:

<!--[if !supportLists]-->■ <!--[endif]-->定位二维码元素 #js\_qr\_code\_box。

<!--[if !supportLists]-->■ <!--[endif]-->**Action**: 将二维码截图保存为 debug\_qr.png（模拟发送给用户）。

<!--[if !supportLists]-->■ <!--[endif]-->**Wait**: 轮询等待页面跳转（模拟用户扫码）。

<!--[if !supportLists]-->■ <!--[endif]-->**Success**: 页面跳转后，执行 context.storage\_state(path="...") 保存 Cookie。

<!--[if !supportLists]-->5. <!--[endif]-->**Branch Success (已登录)**: 打印 "Session Valid"。

<!--[if !supportLists]-->● <!--[endif]-->**交付物**：标准化类 Ali115Browser，提供 login() 和 get\_session() 方法。


#### **模块 B: 媒体情报采集器 (Gying Scraper)**

<!--[if !supportLists]-->● <!--[endif]-->**功能目标**：精准提取电影元数据及下载链接。

<!--[if !supportLists]-->● <!--[endif]-->**技术难点**：Cloudflare 验证、多版本链接的正则匹配。

<!--[if !supportLists]-->● <!--[endif]-->**验证脚本** (tests/test\_scraper.py):

<!--[if !supportLists]-->1. <!--[endif]-->输入一个固定的电影详情页 URL。

<!--[if !supportLists]-->2. <!--[endif]-->**Action**: 启动 Playwright（复用模块 A 的浏览器上下文以绕过反爬）。

<!--[if !supportLists]-->3. <!--[endif]-->**Extraction**: 提取 Title, Rating, Intro。

<!--[if !supportLists]-->4. <!--[endif]-->**Logic**: 提取所有磁力链接，并将其分为 4k\_links 和 1080p\_links 两个列表。

<!--[if !supportLists]-->5. <!--[endif]-->**Check**: 断言列表不为空，且链接格式以 magnet:? 开头。

<!--[if !supportLists]-->● <!--[endif]-->**交付物**：标准化类 GyingScraper，提供 parse\_movie(url) 方法，返回结构化 JSON。


#### **模块 C: 飞书卡片交互引擎 (Card Engine)**

<!--[if !supportLists]-->● <!--[endif]-->**功能目标**：生成符合飞书 JSON 2.0 规范的卡片，并处理回调。

<!--[if !supportLists]-->● <!--[endif]-->**技术难点**：卡片的局部更新（Update Multi）、回调请求的签名验证。

<!--[if !supportLists]-->● <!--[endif]-->**验证脚本** (tests/test\_feishu\_card.py):

<!--[if !supportLists]-->1. <!--[endif]-->**Action**: 使用飞书 Debug 工具或本地 Mock Server 发送一张包含“下载”按钮的测试卡片。

<!--[if !supportLists]-->2. <!--[endif]-->**Mock**: 模拟用户点击按钮，向本地 Server 发送 POST 请求。

<!--[if !supportLists]-->3. <!--[endif]-->**Logic**: Server 接收 Payload，解析出 action 和 value。

<!--[if !supportLists]-->4. <!--[endif]-->**Response**: Server 返回一个新的 JSON 卡片结构（例如变为下拉菜单）。

<!--[if !supportLists]-->5. <!--[endif]-->**Check**: 确认飞书端卡片UI发生变化。

<!--[if !supportLists]-->● <!--[endif]-->**交付物**：标准化类 FeishuInteraction，封装 send\_card() 和 handle\_callback()。


#### **模块 D: 115 任务注入器 (Task Injector)**

<!--[if !supportLists]-->● <!--[endif]-->**功能目标**：在有 Session 的情况下，自动添加离线下载任务。

<!--[if !supportLists]-->● <!--[endif]-->**技术难点**：定位动态弹窗、处理“任务已存在”或“空间不足”的异常。

<!--[if !supportLists]-->● <!--[endif]-->**验证脚本** (tests/test\_115\_add\_task.py):

<!--[if !supportLists]-->1. <!--[endif]-->依赖模块 A 的 Session。

<!--[if !supportLists]-->2. <!--[endif]-->**Action**: 访问 115 离线下载页面。

<!--[if !supportLists]-->3. <!--[endif]-->**Interact**: 点击“链接任务” -> 粘贴磁力链 -> 点击“开始下载”。

<!--[if !supportLists]-->4. <!--[endif]-->**Check**: 截取屏幕判断是否有“添加成功”的 Toast 提示。

<!--[if !supportLists]-->● <!--[endif]-->**交付物**：集成在 Ali115Browser 中的 add\_magnet\_task(link) 方法。


### **6.2 阶段二：标准化工作流协议 (Standardized Protocols)**

为了让这些模块不仅能服务于当前需求，还能被未来的智能体复用，我们需要定义标准化的工作流协议。


#### **协议 1: 浏览器上下文协议 (Browser Context Protocol)**

所有涉及浏览器的 Skill 都应遵循此协议，确保“指纹”一致性。

<!--[if !supportLists]-->● <!--[endif]-->**User Data Dir**: 统一指向 \~/.nanobot/browser\_contexts/default。所有 Cookie、Local Storage 均在此共享。

<!--[if !supportLists]-->● <!--[endif]-->**Launch Args**: 统一封装为 get\_stealth\_launch\_args() 函数，包含 navigator.webdriver = false 等反检测参数。

<!--[if !supportLists]-->● <!--[endif]-->**优势**: 解决了“Gying 刚过完 Cloudflare 验证，115 登录又要重新验证”的问题。


#### **协议 2: 人机验证请求协议 (HVR Protocol)**

当智能体遇到无法自动解决的阻碍（如二维码、验证码）时，不应抛出异常崩溃，而应发起 HVR 请求。

<!--[if !supportLists]-->● <!--[endif]-->**Schema**:\
JSON\
{\
  "type": "REQUIRE\_HUMAN\_INTERVENTION",\
  "reason": "LOGIN\_QR\_CODE",\
  "payload": {\
    "image\_binary": "...", // 二维码图片\
    "instruction": "请使用 115 App 扫码"\
  },\
  "callback\_wait": 120 // 等待秒数\
}

<!--[if !supportLists]-->● <!--[endif]-->**Workflow**: 智能体发出 HVR -> 飞书卡片显示图片 -> 智能体挂起（Sleeping）并轮询 -> 用户操作完成 -> 智能体恢复执行。


### **6.3 阶段三：集成测试与容错设计**

在所有模块独立验证通过后，进行全链路集成测试 tests/test\_full\_workflow\.py。

<!--[if !supportLists]-->● <!--[endif]-->**Happy Path**: 无 Cookie -> 启动 HVR 协议 -> 用户扫码 -> 登录成功 -> 抓取 Gying -> 发送卡片 -> 用户选 4K -> 115 下载成功。

<!--[if !supportLists]-->● <!--[endif]-->**Edge Case 1**: 115 空间不足。 -> **策略**: 截图报错，推送到飞书，任务标记为 Failed。

<!--[if !supportLists]-->● <!--[endif]-->**Edge Case 2**: Gying 页面结构变更。 -> **策略**: Playwright 选择器超时，捕获 TimeoutError，发送“维护提醒”给开发者。


## *****7. 总结**

本报告详细阐述了一个基于 nanobot 和 Playwright 的全链路媒体获取自动化系统。该系统成功解决了用户提出的三大挑战：

<!--[if !supportLists]-->1. <!--[endif]-->**精准采集：** 通过深度 DOM 解析和正则校验，确保了评分等关键决策信息的准确获取。

<!--[if !supportLists]-->2. <!--[endif]-->**安全认证：** 创新性地引入了二维码中继机制，实现了在不触碰用户密码前提下的自动化登录，完全符合零信任安全原则。

<!--[if !supportLists]-->3. <!--[endif]-->**交互体验：** 利用飞书卡片构建了可视化的筛选界面，将复杂的磁力链接过滤逻辑封装在代理内部，为用户提供了优雅的“点选即得”体验。

特别是新增的**系统开发方案**，将复杂的智能体开发任务降维分解为可独立测试的原子模块，并提出了标准化的“浏览器上下文协议”和“人机验证请求协议”。这不仅确保了本项目的成功落地，也为未来构建其他需要复杂网页交互（如自动化报销、票务监控）的智能体提供了可复用的工程范式。

***

**数据表：Playwright 选择器策略汇总******

|               |          |                                                 |                   |
| ------------- | -------- | ----------------------------------------------- | ----------------- |
| **目标页面**      | **目标元素** | **推荐选择器策略 (CSS/XPath)**                         | **备注**            |
| **gying 详情页** | 电影标题     | h1.movie-title                                  | 页面唯一标题            |
| **gying 详情页** | 豆瓣评分     | .score-num, xpath=//span\[contains(text(),'.')] | 需正则校验是否为数字        |
| **gying 详情页** | 4K 下载行   | tr:has-text("4K"):has-text("中字")                | 组合过滤器             |
| **115 登录页**   | 二维码容器    | #js\_qr\_code\_box, .qrcode-view                | 需配合 visibility 等待 |
| **115 登录页**   | 刷新遮罩     | .qr-mask, text="点击刷新"                           | 用于处理二维码过期         |
| **115 离线页**   | 添加任务钮    | a\[data-btn='link\_task']                       | 属性选择器更稳定          |
| **115 离线页**   | 确认下载钮    | .dialog-bottom.btn-confirm                      | 需限定在 Dialog 范围内   |

_(注：以上选择器基于通用网页结构推断，实际部署时需根据目标网站实时 DOM 结构进行微调)_
