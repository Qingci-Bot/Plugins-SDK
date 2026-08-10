# Qingci-Bot 插件开发工作区

独立于主项目的插件开发环境，包含完整的 SDK 和模板。

## 快速开始

```bash
# 1. 安装 SDK
pip install -e .

# 2. 验证安装
python -c "from qingci_plugin_sdk import PluginBase, on_command; print('OK')"

# 3. 从模板创建插件
cp plugins/_template.py plugins/my_plugin.py

# 4. 编辑 my_plugin.py，修改类名和 name 属性

# 5. 开发完成后，复制到 Qingci-Bot 的 plugins/ 目录
cp plugins/my_plugin.py ../Qingci-Bot/plugins/
```

## 目录结构

```
Plugins-Dev/
├── README.md
├── pyproject.toml
├── .gitignore
├── qingci_plugin_sdk/    # 插件 SDK（零外部依赖）
│   ├── base.py           # PluginBase 基类
│   ├── matcher.py        # Matcher + 工厂函数
│   ├── rule.py           # Rule + 内置规则
│   ├── permission.py     # Permission + 内置权限
│   ├── ratelimit.py      # RateLimiter
│   └── context.py        # MessageContext
└── plugins/              # 你的插件源码
    ├── _template.py      # 完整开发模板（不被加载）
    └── hello.py          # 最小示例
```

## SDK API

### 插件基类

```python
from qingci_plugin_sdk import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"
    author = "YourName"
    description = "我的插件"
    require = []  # 依赖的其他插件 name

    async def on_load(self):
        # 注册 Matcher、定时任务等
        pass

    async def on_unload(self):
        # 清理资源
        pass
```

### Matcher 工厂函数

| 函数 | 触发方式 | 示例 |
|------|---------|------|
| `on_command(cmd)` | `/命令` 或 `命令` | `on_command("ping")` |
| `on_startswith(prefix)` | 消息前缀 | `on_startswith("天气")` |
| `on_keyword(kws)` | 包含关键词 | `on_keyword(("帮助", "help"))` |
| `on_message(rule)` | 所有消息 | `on_message(rule=command("admin"))` |
| `on_notice()` | 通知事件 | 群成员变更 |
| `on_request()` | 请求事件 | 加好友/加群 |

### Rule 规则

```python
from qingci_plugin_sdk import command, startswith, keyword, regex, to_me, is_private, is_group

# 规则组合
rule = command("ping") & to_me()          # AND
rule = is_private() | is_group()          # OR
rule = ~is_private()                      # NOT
```

### Permission 权限

```python
from qingci_plugin_sdk import EVERYONE, SUPERUSER, GROUP, PRIVATE, USER

permission = SUPERUSER & PRIVATE          # 仅管理员私聊
permission = USER(123456)                 # 指定用户
```

### 依赖注入

在 `on_load` 中通过 `self` 访问框架注入的依赖：

| 属性 | 说明 |
|------|------|
| `self.bot` | Bot 主实例 |
| `self.db` | 数据库（异步 API） |
| `self.config` | 配置管理器 |
| `self.connection` | OneBot 连接 |
| `self.llm` | LLM 管理器 |
| `self.scheduler` | 定时任务（可能为 None） |
| `self.tool_registry` | Function Calling 工具注册表（可能为 None） |
| `self.knowledge_store` | 知识库（可能为 None） |

### MatcherContext

handler 接收 `MatcherContext` 参数，继承自 `MessageContext`：

```python
async def handler(ctx: MatcherContext) -> str:
    ctx.user_id       # 发送者 QQ
    ctx.group_id      # 群号（私聊为 0）
    ctx.plain_text    # 纯文本消息
    ctx.command       # 匹配的命令名
    ctx.args          # 命令参数
    ctx.is_at_bot     # 是否 @ 了 Bot
    ctx.sender_name   # 发送者昵称
    ctx.raw_event     # 原始 OneBot 事件
```

## 发布插件

开发完成后，将 `.py` 文件放入 Qingci-Bot 的 `plugins/` 目录，重启 Bot 或通过 Web UI 热重载即可。

## 许可

GPL-3.0-or-later