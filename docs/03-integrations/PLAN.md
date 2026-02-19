# DOCUMENT METADATA
title: 重构计划：集成工具动态加载
filename: PLAN.md
status: Approved
version: 1.0.0
owner: AI Assistant
last_updated: 2026-02-16
---

## Document History
| Version | Date       | Author | Description of Changes |
|---------|------------|--------|------------------------|
| 1.0.0   | 2026-02-16 | Claude | Initial creation       |

## Purpose & Scope
> 将集成工具从硬编码注册改为目录扫描 + 自带配置的动态加载模式，实现平台化扩展。

---

# 重构计划：集成工具动态加载

## 背景

当前 cloud115 和 gying 集成工具硬编码在 `loop.py` 的 `_register_default_tools()` 中，配置模型硬编码在 `schema.py` 中。每新增一个集成都需要修改 3 个核心文件（loop.py、schema.py、commands.py），不具备平台化扩展性。

**目标：** 将集成工具改为目录扫描 + 自带配置的模式。新增集成只需在 `integrations/` 目录下放置文件，无需修改任何核心代码。

## 目录结构

```
nanobot/agent/tools/integrations/
├── __init__.py              # 导出 IntegrationLoader
├── loader.py                # IntegrationLoader 核心类
├── cloud115/
│   ├── __init__.py          # 空
│   ├── config.py            # Cloud115Config（从 schema.py 迁移）
│   └── tool.py              # Cloud115Tool + TOOLS 描述符
└── gying/
    ├── __init__.py          # 空
    ├── config.py            # GyingConfig（从 schema.py 迁移）
    └── tool.py              # GyingScraperTool + GyingUpdatesTool + TOOLS 描述符
```

## 核心设计

### TOOLS 描述符协议

每个 `tool.py` 末尾声明 `TOOLS` 列表，告诉 loader 如何实例化工具：

```python
TOOLS = [
    {
        "class": Cloud115Tool,
        "config_map": {                          # 配置字段 → 构造函数参数
            "session_path": "session_path",
            "default_save_path": "default_save_path",
        },
    },
]
```

gying 的 GyingUpdatesTool 需要 workspace 路径，用 `workspace_fields` 声明：

```python
{
    "class": GyingUpdatesTool,
    "config_map": {"browser_data_dir": "browser_data_dir", "headless": "headless"},
    "workspace_fields": {"seen_file": "film_download/seen_movies.json"},
}
```

### IntegrationLoader 工作流程

1. 扫描 `integrations/` 目录，发现含 `tool.py` 的子目录
2. 从 `config.integrations` 取对应的配置 dict
3. 如果 `enabled != true`，跳过
4. 导入 `config.py`，用 Pydantic model 验证配置
5. 导入 `tool.py`，读取 `TOOLS` 描述符
6. 按 `config_map` 映射配置到构造参数，实例化工具，注册到 registry
7. ImportError 只禁用该集成，不影响其他

### 配置兼容性策略

`schema.py` 中的 `IntegrationsConfig` 保留，但配置模型改为从集成目录 re-import：

```python
# schema.py - 配置模型改为 re-import
from nanobot.agent.tools.integrations.cloud115.config import Cloud115Config
from nanobot.agent.tools.integrations.gying.config import GyingConfig

class IntegrationsConfig(BaseModel):
    cloud115: Cloud115Config = Field(default_factory=Cloud115Config)
    gying: GyingConfig = Field(default_factory=GyingConfig)
```

config.json 格式不变，所有现有测试不需修改。

## 实施步骤

### Step 1：创建集成包目录和 `__init__.py`

- `nanobot/agent/tools/integrations/__init__.py`
- `nanobot/agent/tools/integrations/cloud115/__init__.py`
- `nanobot/agent/tools/integrations/gying/__init__.py`

### Step 2：创建 config.py（从 schema.py 迁移配置模型）

- `integrations/cloud115/config.py` ← 从 `schema.py` 的 `Cloud115Config` 迁出
- `integrations/gying/config.py` ← 从 `schema.py` 的 `GyingConfig` 迁出

### Step 3：创建 tool.py（迁移工具类 + 添加 TOOLS 描述符）

- `integrations/cloud115/tool.py` ← 从 `nanobot/agent/tools/cloud115.py` 迁移全部代码，末尾加 TOOLS
- `integrations/gying/tool.py` ← 从 `nanobot/agent/tools/gying.py` 迁移全部代码，末尾加 TOOLS

### Step 4：创建 IntegrationLoader

- `integrations/loader.py`：~130 行
- 关键方法：`load_all(registry, config)`、`_discover_integrations()`、`_load_integration()`
- 支持 `IntegrationsConfig` 对象和 raw dict 两种输入

### Step 5：创建向后兼容 shim

旧的导入路径保留为 re-export：
- `nanobot/agent/tools/cloud115.py` → 2 行 re-export
- `nanobot/agent/tools/gying.py` → 5 行 re-export（含 SELECTORS、BASE_URL）

### Step 6：更新 schema.py

- 删除 `Cloud115Config`、`GyingConfig` 的本地定义
- 改为从 `integrations/cloud115/config.py` 和 `integrations/gying/config.py` re-import
- `IntegrationsConfig` 保留，字段类型不变

### Step 7：更新 loop.py

替换 `_register_default_tools()` 中 112-136 行的硬编码块为：

```python
if self.config:
    from nanobot.agent.tools.integrations.loader import IntegrationLoader
    loader = IntegrationLoader(workspace=self.workspace)
    loader.load_all(self.tools, self.config.integrations)
```

### Step 8：新增 IntegrationLoader 测试

- `tests/test_integration_loader.py`：~7 个测试
- 覆盖：发现集成、启用/禁用注册、raw dict 输入、None 输入、workspace_fields

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `integrations/__init__.py` | 包初始化 |
| 新建 | `integrations/loader.py` | IntegrationLoader 核心 |
| 新建 | `integrations/cloud115/__init__.py` | 空 |
| 新建 | `integrations/cloud115/config.py` | Cloud115Config |
| 新建 | `integrations/cloud115/tool.py` | Cloud115Tool + TOOLS |
| 新建 | `integrations/gying/__init__.py` | 空 |
| 新建 | `integrations/gying/config.py` | GyingConfig |
| 新建 | `integrations/gying/tool.py` | GyingScraperTool + GyingUpdatesTool + TOOLS |
| 新建 | `tests/test_integration_loader.py` | loader 测试 |
| 改写 | `nanobot/agent/tools/cloud115.py` | 替换为 re-export shim |
| 改写 | `nanobot/agent/tools/gying.py` | 替换为 re-export shim |
| 修改 | `nanobot/config/schema.py` | 配置模型改为 re-import |
| 修改 | `nanobot/agent/loop.py` | 25 行硬编码 → 5 行 loader 调用 |

**不需要修改的文件：** 所有 7 个现有测试文件、commands.py、loader.py、base.py、registry.py、skills.py

## 验证方案

```bash
# 1. 运行全部现有测试（63 个，不应有任何失败）
pytest -v

# 2. 运行新增的 loader 测试
pytest tests/test_integration_loader.py -v

# 3. lint 检查所有变更文件
ruff check nanobot/agent/tools/integrations/ nanobot/config/schema.py nanobot/agent/loop.py tests/test_integration_loader.py

# 4. 验证配置加载
python -c "
from nanobot.config import load_config
c = load_config()
print(f'cloud115: {c.integrations.cloud115.enabled}')
print(f'gying: {c.integrations.gying.enabled}')
"

# 5. 验证向后兼容导入
python -c "
from nanobot.agent.tools.cloud115 import Cloud115Tool
from nanobot.agent.tools.gying import GyingScraperTool, GyingUpdatesTool
from nanobot.config.schema import Cloud115Config, GyingConfig, IntegrationsConfig
print('All backward-compat imports OK')
"
```
