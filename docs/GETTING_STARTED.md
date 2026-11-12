# 快速上手

> 环境准备、5 分钟跑通插件开发、从零写第一个插件、开发工作区结构。面向第一次接触 Qingci-Bot 插件开发的读者。

## 准备工作

在开始之前，你需要确保电脑上已经安装了以下工具：

| 工具 | 用途 | 检查方式 |
|------|------|---------|
| Python 3.10+ | 编程语言 | `python --version` |
| uv | Python 包管理器 | `uv --version` |
| 代码编辑器 | 写代码 | 推荐 [VS Code](https://code.visualstudio.com/) |

> **关于 Python 版本**：SDK 本身支持 3.10+（CI 覆盖 3.10–3.14），但**宿主** Qingci-Bot-CE 从 1.19.0 起要求 **3.11+**。若插件只在主项目里跑，直接按 3.11+ 开发即可，避免用到 3.10 上没有的语法。

> **没有 uv？** 在终端执行 `pip install uv` 即可安装。uv 比 pip 更快，是推荐的包管理工具。
>
> **没有 Python？** 去 [python.org](https://www.python.org/downloads/) 下载安装，安装时勾选「Add Python to PATH」。

---

## 5 分钟上手

下面带你从零开始，跑通插件开发环境。

### 第一步：打开终端

在 `Plugins-SDK` 文件夹上右键，选择「在终端中打开」（或 `cd` 到该目录）。

### 第二步：创建虚拟环境

用 uv 创建虚拟环境，比 `python -m venv` 更快：

```bash
uv venv
```

### 第三步：激活虚拟环境

```bash
# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

激活后，终端前面会出现 `(.venv)` 标识，说明虚拟环境已生效。

> **提示**：每次打开新终端都需要重新激活。VS Code 用户可以在右下角选择 `.venv` 作为 Python 解释器，终端会自动激活。

### 第四步：安装 SDK

上面的流程假设你克隆了本仓库、要在本地改 SDK 源码，所以用**可编辑安装**：

```bash
uv pip install -e .
```

这条命令把 `qingci_plugin_sdk` 这个包安装到虚拟环境中，之后你就可以在代码里
`from qingci_plugin_sdk import ...` 了；改动 SDK 源码会立即生效。

如果你只是写插件、不需要改 SDK 源码，直接装 [PyPI](https://pypi.org/project/qingci-plugin-sdk/) 上的发布版即可，
不用克隆本仓库：

```bash
uv add qingci-plugin-sdk      # 或 pip install qingci-plugin-sdk
```

两种方式装出来的导入名都是 `qingci_plugin_sdk`，插件代码无需区分。本教程后续步骤仍以
「克隆了本仓库」为前提，继续使用可编辑安装。

### 第五步：验证安装

```bash
python -c "from qingci_plugin_sdk import PluginBase, on_command; print('安装成功!')"
```

如果看到 `安装成功!`，说明环境已经就绪。

### 第六步：从模板创建插件

```bash
# Windows
xcopy /E /I plugins\_template plugins\my_plugin

# Mac / Linux
cp -r plugins/_template plugins/my_plugin
```

### 第七步：编辑你的插件

用代码编辑器打开 `plugins/my_plugin/__init__.py`，找到这一段：

```python
class TemplatePlugin(PluginBase):
    name = "template"  # 改成你的插件名，比如 "my_plugin"
    author = "YourName"  # 改成你的名字
```

把 `name` 和 `author` 改成你自己的，然后保存。

### 第八步：放到主项目里运行

把插件复制到主项目 **Qingci-Bot-CE** 的插件目录（源码运行时为 `Qingci-Bot-CE/plugins/`；实例模式下为 `Qingci-Bot-CE/instances/<name>/plugins/`，下例以 `default` 实例为例）：

```bash
# Windows
xcopy /E /I plugins\my_plugin ..\Qingci-Bot-CE\instances\default\plugins\my_plugin

# Mac / Linux
cp -r plugins/my_plugin ../Qingci-Bot-CE/instances/default/plugins/
```

重启 Qingci-Bot，你的插件就会自动加载了！

---

## 你的第一个插件

让我们从零开始，写一个完整的插件。这个插件会做三件事：

1. 用户发 `/hello`，机器人回复「你好！」
2. 用户发「天气 北京」，机器人回复「查询北京的天气...」
3. 用户发消息包含「帮助」，机器人回复帮助信息

### 1. 创建插件目录

在 `plugins/` 目录下新建文件夹 `my_first_plugin/`，在其中创建 `__init__.py`：

```
plugins/my_first_plugin/
└── __init__.py    # 插件入口（必需）
```

把下面的代码写入 `__init__.py`：

```python
"""我的第一个插件"""

import logging
from qingci_plugin_sdk import (
    PluginBase,
    PluginStatus,  # 插件状态枚举
    MatcherContext,
    on_command,
    on_startswith,
    on_keyword,
)

logger = logging.getLogger("qingci-bot.plugin.my_first")


class MyFirstPlugin(PluginBase):
    # ===== 插件信息 =====
    name = "my_first"  # 唯一标识，不能跟其他插件重名
    version = "1.0.0"
    author = "你的名字"
    description = "我的第一个插件"

    # ===== 插件加载 =====
    async def on_load(self):
        """插件加载时，在这里注册你的功能"""
        # 功能1: /hello 命令
        self.matchers.append(on_command("hello", priority=1)(self._handle_hello))

        # 功能2: "天气 xxx" 前缀
        self.matchers.append(on_startswith("天气", priority=10)(self._handle_weather))

        # 功能3: 关键词"帮助"
        self.matchers.append(on_keyword("帮助", priority=5)(self._handle_help))

        logger.info("我的第一个插件已加载！")

    # ===== 插件卸载 =====
    async def on_unload(self):
        logger.info("我的第一个插件已卸载")

    # ===== 功能实现 =====

    async def _handle_hello(self, ctx: MatcherContext) -> str:
        """处理 /hello 命令"""
        name = ctx.args.strip() or "朋友"
        return f"你好，{name}！"

    async def _handle_weather(self, ctx: MatcherContext) -> str:
        """处理 '天气 xxx' 前缀"""
        city = ctx.args.strip() or "未知城市"
        return f"查询 {city} 的天气中..."

    async def _handle_help(self, ctx: MatcherContext) -> str:
        """处理 '帮助' 关键词"""
        return "可用命令: /hello, 天气 <城市>, 帮助"
```

### 2. 代码解释

让我们逐段理解上面的代码：

| 代码 | 解释 |
|------|------|
| `name = "my_first"` | 插件的唯一标识，不能和其他插件重名 |
| `async def on_load(self)` | 插件加载时自动调用，在这里注册功能 |
| `async def on_unload(self)` | 插件卸载时自动调用，用于清理资源 |
| `self.matchers.append(...)` | 注册一个功能模块 |
| `on_command("hello")` | 匹配 `/hello` 或 `hello` 开头的消息 |
| `on_startswith("天气")` | 匹配以「天气」开头的消息 |
| `on_keyword("帮助")` | 匹配包含「帮助」的消息 |
| `ctx.args` | 命令参数，如 `天气 北京` 中 `ctx.args` = `"北京"` |
| `return "..."` | 返回的字符串会作为消息发送给用户 |

### 3. 关键概念

**handler 函数**就是 `_handle_hello`、`_handle_weather` 这样的函数。它们：
- 接收一个 `ctx: MatcherContext` 参数，里面包含了消息的所有信息
- 返回一个字符串，这个字符串就是机器人发给用户的回复
- 返回 `None` 表示不回复（让其他插件处理）

---

## 项目结构

```
Plugins-SDK/
├── README.md                # 门面：定位 / 文档导航 / 特性 / 极简示例
├── docs/                    # 开发文档（快速上手 / 开发指南 / API 参考 / 发布与 FAQ）
├── pyproject.toml           # 项目配置（包名、版本、依赖）
├── uv.lock                  # 依赖锁定文件
├── .gitignore               # Git 忽略规则
├── LICENSE                  # GPL-3.0 官方全文（仅占位符填项目名/版权人）
├── NOTICE                   # 版权人声明与组织授权（CE 另有 §7 附加条款）
├── qingci_plugin_sdk/       # 插件 SDK（零外部依赖，纯 Python；插件协议层的唯一来源）
│   ├── __init__.py          # 统一导出所有 API
│   ├── base.py              # PluginBase 插件基类（旧式 on_message/on_notice/on_request 已弃用）
│   ├── context.py           # MessageContext 消息上下文（主项目 dispatcher 转发同一类型）
│   ├── events.py            # 类型化事件（notice/request 事件模型 + 解析工厂）
│   ├── matcher.py           # Matcher 匹配器 + 工厂函数
│   ├── rule.py              # Rule 规则系统 + 内置规则
│   ├── segments.py          # OneBot 12 消息段抽象（Message/MessageSegment + v11↔v12 转换）
│   ├── permission.py        # Permission 权限系统 + 内置权限
│   ├── ratelimit.py         # RateLimiter 限流器
│   ├── session.py           # 会话阶梯（多轮交互）：Session + Pause/Finish/Reject 异常
│   ├── i18n.py              # I18n 国际化翻译器
│   ├── llm_tool.py          # @llm_tool 插件级 LLM 工具声明
│   ├── media.py             # 图片引用解析（file_id → URL/data URI，多模态输入）
│   └── paths.py             # app_root 路径解析 + data_root 覆盖钩子（供 data_dir 使用）
├── tests/                   # SDK 单元测试（pytest）
└── plugins/                 # 你的插件源码都放在这里
    └── _template/           # 完整开发模板（以 _ 开头，不会被加载）
        └── __init__.py
```

> 最小示例插件已迁移至独立仓库 [Qingci-Bot/hello](https://github.com/Qingci-Bot/hello)（仓库根即插件源码），可在插件市场安装，也可作新仓库模板。

> **提示**：以 `_` 开头的目录不会被 Qingci-Bot 自动加载，所以 `_template/` 放在这里很安全，不会影响运行。

---
