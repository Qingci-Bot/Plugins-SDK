# Qingci-Bot 插件开发工作区

> 本项目底层核心代码由 **Zhou Zhe (aka luoqingci)** 原创，并授予 [Qingci-Bot](https://atomgit.com/Qingci-Bot) 组织持续开发。

> 零基础也能看懂的插件开发指南。读完这篇文档，你就能写出自己的 QQ 机器人插件。

独立于主项目的插件开发环境，包含完整的 SDK 和模板。你只需要一台电脑、一个代码编辑器，就可以开始开发插件。

> 主项目：[Qingci-Bot](https://atomgit.com/Qingci-Bot/Qingci-Bot-CE) — 基于 Python 的 QQ 机器人框架

---

## 目录

- [准备工作](#准备工作)
- [5 分钟上手](#5-分钟上手)
- [你的第一个插件](#你的第一个插件)
- [项目结构](#项目结构)
- [核心概念](#核心概念)
  - [命名规范](#命名规范)
  - [插件基类 PluginBase](#插件基类-pluginbase)
  - [匹配器 Matcher](#匹配器-matcher)
  - [规则 Rule](#规则-rule)
  - [权限 Permission](#权限-permission)
  - [上下文 MatcherContext](#上下文-matchercontext)
  - [依赖注入](#依赖注入)
- [完整 API 参考](#完整-api-参考)
- [常见场景](#常见场景)
  - [发送消息到 QQ](#发送消息到-qq)
  - [调用大模型](#调用大模型)
  - [定时任务](#定时任务)
  - [Function Calling](#function-calling)
  - [一次性匹配器](#一次性匹配器)
  - [模块级装饰器](#模块级装饰器)
- [发布插件](#发布插件)
- [常见问题](#常见问题)
- [许可](#许可)

---

## 准备工作

在开始之前，你需要确保电脑上已经安装了以下工具：

| 工具 | 用途 | 检查方式 |
|------|------|---------|
| Python 3.10+ | 编程语言 | `python --version` |
| uv | Python 包管理器 | `uv --version` |
| 代码编辑器 | 写代码 | 推荐 [VS Code](https://code.visualstudio.com/) |

> **没有 uv？** 在终端执行 `pip install uv` 即可安装。uv 比 pip 更快，是推荐的包管理工具。
>
> **没有 Python？** 去 [python.org](https://www.python.org/downloads/) 下载安装，安装时勾选「Add Python to PATH」。

---

## 5 分钟上手

下面带你从零开始，跑通插件开发环境。

### 第一步：打开终端

在 `Plugins-Dev` 文件夹上右键，选择「在终端中打开」（或 `cd` 到该目录）。

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

```bash
uv pip install -e .
```

这条命令做了什么？它把 `qingci_plugin_sdk` 这个包安装到虚拟环境中，之后你就可以在代码里 `from qingci_plugin_sdk import ...` 了。

### 第五步：验证安装

```bash
python -c "from qingci_plugin_sdk import PluginBase, on_command; print('安装成功!')"
```

如果看到 `安装成功!`，说明环境已经就绪。

### 第六步：从模板创建插件

```bash
# Windows
copy plugins\_template.py plugins\my_plugin.py

# Mac / Linux
cp plugins/_template.py plugins/my_plugin.py
```

### 第七步：编辑你的插件

用代码编辑器打开 `plugins/my_plugin.py`，找到这一段：

```python
class TemplatePlugin(PluginBase):
    name = "template"       # 改成你的插件名，比如 "my_plugin"
    author = "YourName"     # 改成你的名字
```

把 `name` 和 `author` 改成你自己的，然后保存。

### 第八步：放到主项目里运行

```bash
# Windows
copy plugins\my_plugin.py ..\Qingci-Bot\plugins\

# Mac / Linux
cp plugins/my_plugin.py ../Qingci-Bot/plugins/
```

重启 Qingci-Bot，你的插件就会自动加载了！

---

## 你的第一个插件

让我们从零开始，写一个完整的插件。这个插件会做三件事：

1. 用户发 `/hello`，机器人回复「你好！」
2. 用户发「天气 北京」，机器人回复「查询北京的天气...」
3. 用户发消息包含「帮助」，机器人回复帮助信息

### 1. 创建插件文件

在 `plugins/` 目录下新建 `my_first_plugin.py`：

```python
"""我的第一个插件"""
import logging
from qingci_plugin_sdk import (
    PluginBase,
    PluginStatus,       # 插件状态枚举
    MatcherContext,
    on_command,
    on_startswith,
    on_keyword,
)

logger = logging.getLogger("qingci-bot.plugin.my_first")


class MyFirstPlugin(PluginBase):
    # ===== 插件信息 =====
    name = "my_first"         # 唯一标识，不能跟其他插件重名
    version = "1.0.0"
    author = "你的名字"
    description = "我的第一个插件"

    # ===== 插件加载 =====
    async def on_load(self):
        """插件加载时，在这里注册你的功能"""
        # 功能1: /hello 命令
        self.matchers.append(
            on_command("hello", priority=1)(self._handle_hello)
        )

        # 功能2: "天气 xxx" 前缀
        self.matchers.append(
            on_startswith("天气", priority=10)(self._handle_weather)
        )

        # 功能3: 关键词"帮助"
        self.matchers.append(
            on_keyword("帮助", priority=5)(self._handle_help)
        )

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
├── README.md                # 你现在看的文档
├── pyproject.toml           # 项目配置（包名、版本、依赖）
├── uv.lock                  # 依赖锁定文件
├── .gitignore               # Git 忽略规则
├── LICENSE                  # GPL-3.0 许可证
├── qingci_plugin_sdk/       # 插件 SDK（零外部依赖，纯 Python）
│   ├── __init__.py          # 统一导出所有 API
│   ├── base.py              # PluginBase 插件基类
│   ├── matcher.py           # Matcher 匹配器 + 工厂函数
│   ├── rule.py              # Rule 规则系统 + 内置规则
│   ├── permission.py        # Permission 权限系统 + 内置权限
│   ├── ratelimit.py         # RateLimiter 限流器
│   └── context.py           # MessageContext 消息上下文
└── plugins/                 # 你的插件源码都放在这里
    ├── _template.py         # 完整开发模板（以 _ 开头，不会被加载）
    └── hello.py             # 最小示例插件
```

> **提示**：以 `_` 开头的 `.py` 文件不会被 Qingci-Bot 自动加载，所以 `_template.py` 放在这里很安全，不会影响运行。

---

## 核心概念

### 命名规范

写插件之前，先了解命名规则。不遵守的话插件无法加载。

| 项目 | 规范 | 正确示例 | 错误示例 |
|------|------|---------|---------|
| 文件名 | 小写英文 + 下划线，与 `name` 一致 | `chat.py`、`my_plugin.py` | `MyPlugin.py`、`_test.py`、`插件.py` |
| 类名 | `{Name}Plugin` 帕斯卡命名 | `ChatPlugin`、`HelloPlugin` | `chat`、`my_plugin` |
| `name` 属性 | 小写英文 + 下划线，唯一标识 | `"chat"`、`"my_plugin"` | `"MyPlugin"`、`"我的插件"` |

**三条硬性规则（违反会报错）：**

1. **文件名不能以 `_` 开头** — `_template.py`、`__init__.py` 会被跳过，不会被加载
2. **一个文件只能有一个插件类** — 每个 `.py` 文件最多定义 1 个 `PluginBase` 子类
3. **`name` 不能跟其他插件重名** — 每个插件的 `name` 是唯一标识

> **建议**：文件名和 `name` 保持一致，类名用 `{Name}Plugin` 格式。这样无论是读代码还是管理插件，一眼就能对得上。

### 插件基类 PluginBase

所有插件都必须继承 `PluginBase`，并实现 `on_load()` 和 `on_unload()` 两个方法。

```python
from qingci_plugin_sdk import PluginBase, PluginStatus

class MyPlugin(PluginBase):
    # ===== 必填 =====
    name = "my_plugin"        # 插件唯一标识

    # ===== 可选 =====
    version = "1.0.0"        # 版本号
    author = "YourName"       # 作者
    description = "我的插件"   # 简介
    category = "tool"         # 分类：chat / admin / tool / fun / 自定义
    require = []              # 依赖的其他插件，支持 PEP 440 版本约束（如 "chat>=1.0,<2.0"）

    async def on_load(self):
        """插件加载时调用 —— 注册功能"""
        pass

    async def on_unload(self):
        """插件卸载时调用 —— 清理资源"""
        pass

    async def on_disable(self):
        """插件被禁用时调用（可选）—— 停用定时任务等轻量清理"""
        pass

    async def on_enable(self):
        """插件被启用时调用（可选）—— 恢复定时任务等"""
        pass
```

**`require` 依赖声明**：如果你的插件需要另一个插件先加载，填写它的 `name`。支持 PEP 440 版本约束：

```python
require = ["chat"]              # 无版本约束
require = ["chat>=1.0,<2.0"]    # 依赖 chat 1.x 版本
require = ["admin>=1.1"]        # 依赖 admin 1.1 及以上
```

**`category` 分类**：插件分类用于前端分类筛选和 `/help` 命令分组展示：

| 分类 | 说明 |
|------|------|
| `chat` | 聊天对话类 |
| `admin` | 管理控制类 |
| `tool` | 工具类 |
| `fun` | 娱乐类 |
| 自定义 | 任意字符串 |

**插件状态（PluginStatus）**：

```python
plugin.status        # PluginStatus.LOADED / DISABLED / ERROR 等
plugin.enabled       # bool，向后兼容：LOADING/LOADED 为 True
```

| 状态 | 值 | 说明 |
|------|------|------|
| `LOADING` | `"loading"` | 正在加载 |
| `LOADED` | `"loaded"` | 已加载，正常运行 |
| `DISABLED` | `"disabled"` | 已禁用，跳过事件分发 |
| `ERROR` | `"error"` | 加载/运行出错 |
| `UNLOADING` | `"unloading"` | 正在卸载 |

### 匹配器 Matcher

匹配器是插件的核心。它定义了「什么样的消息触发什么样的功能」。

Qingci-Bot 提供了 6 种工厂函数来创建匹配器：

| 工厂函数 | 触发条件 | 适合场景 |
|----------|---------|---------|
| `on_command(cmd)` | 消息以 `/命令` 或 `命令` 开头 | 命令类功能，如 `/ping`、`/help` |
| `on_startswith(prefix)` | 消息以指定文字开头 | 前缀类功能，如 `天气 北京` |
| `on_keyword(kws)` | 消息包含指定关键词 | 关键词触发，如含「帮助」就回复 |
| `on_message(rule)` | 所有消息（需配合规则过滤） | 需要精细控制匹配条件 |
| `on_notice()` | 通知事件（群成员增减等） | 监听群事件 |
| `on_request()` | 请求事件（加好友/加群） | 处理好友申请 |

**注册方式**：

```python
async def on_load(self):
    # 方式1: 插件内注册（推荐，可以访问 self）
    self.matchers.append(
        on_command("ping", priority=1)(self._handle_ping)
    )

    # 方式2: 模块级装饰器（在类外面写）
    # 见下方「常见场景」章节
```

**匹配器参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `rule` | `Rule` | `None` | 额外的匹配规则 |
| `permission` | `Permission` | `EVERYONE` | 权限要求 |
| `priority` | `int` | `1` | 优先级，越小越先执行 |
| `block` | `bool` | `True` | 匹配后是否阻止后续匹配器 |
| `temp` | `bool` | `False` | 是否一次性（触发后自动移除） |
| `description` | `str` | `""` | 功能描述（显示在 `/help` 中） |

**priority 优先级**：

```
priority=1  最先执行（如 /help 命令）
priority=5  中间执行
priority=10 最后执行（如兜底回复）
priority=100 最后最后执行
```

### 规则 Rule

规则用来过滤消息。你可以用 `&`（AND）、`|`（OR）、`~`（NOT）组合规则。

**内置规则**：

| 规则 | 说明 | 示例 |
|------|------|------|
| `command("ping")` | 匹配 `/ping` 或 `ping` 命令 | 支持别名：`command(("ping", "p"))` |
| `startswith("天气")` | 匹配以「天气」开头 | 自动把后续文本写入 `ctx.args` |
| `endswith("吗")` | 匹配以「吗」结尾 | |
| `fullmatch("你好")` | 完全等于「你好」 | |
| `contains("秘密")` | 包含「秘密」 | |
| `keyword("帮助", "help")` | 包含关键词（词边界匹配） | 比 contains 更精确 |
| `regex(r"\d+")` | 正则匹配 | 匹配结果写入 `ctx.match` |
| `to_me()` | @ 机器人 或 私聊 | |
| `is_private()` | 私聊消息 | |
| `is_group()` | 群聊消息 | |
| `rate_limit()` | 限流规则 | 配合 config 限流 |

**规则组合示例**：

```python
# 只有 @ 机器人 且 是命令 才触发
rule = to_me() & command("ping")

# 私聊或群聊都可以
rule = is_private() | is_group()

# 非私聊（即群聊）
rule = ~is_private()

# 复杂组合：管理员发送的 /admin 命令，且是私聊
rule = command("admin") & is_private()
```

### 权限 Permission

权限控制「谁能用这个功能」。

**内置权限**：

| 权限 | 说明 |
|------|------|
| `EVERYONE` | 所有人（默认） |
| `SUPERUSER` | 超级管理员（config 中 `admin_users` 列表里的 QQ） |
| `ADMIN` | 管理员（与 SUPERUSER 等价） |
| `PRIVATE` | 仅限私聊 |
| `GROUP` | 仅限群聊 |
| `MEMBER` | 普通群员（与 EVERYONE 等价） |
| `USER(qq)` | 指定 QQ 用户可用 |
| `GROUP_MEMBER(qq)` | 指定群成员可用 |

**权限组合**：

```python
# 仅管理员私聊
permission = SUPERUSER & PRIVATE

# 管理员或指定用户
permission = SUPERUSER | USER(123456789)

# 指定用户123456在私聊中
permission = USER(123456) & PRIVATE
```

### 上下文 MatcherContext

handler 函数接收的 `ctx` 参数包含了当前消息的所有信息：

```python
async def handler(ctx: MatcherContext) -> str:
    # 发送者信息
    ctx.user_id        # 发送者 QQ 号 (int)
    ctx.sender_name    # 发送者昵称 (str)
    ctx.group_id       # 群号，私聊时为 0 (int)

    # 消息内容
    ctx.plain_text     # 纯文本消息 (str)
    ctx.raw_message    # 原始消息（含 CQ 码）(str)
    ctx.images         # 图片 URL 列表 (list[str])

    # 命令解析（由 command/startswith 规则自动填充）
    ctx.command        # 匹配到的命令名 (str)
    ctx.args           # 命令参数 (str)

    # 正则匹配（由 regex 规则自动填充）
    ctx.match          # re.Match 对象

    # 状态
    ctx.is_at_bot      # 是否 @ 了机器人 (bool)
    ctx.message_type   # "group" 或 "private" (str)

    # 原始事件
    ctx.raw_event      # OneBot 原始事件 dict

    # 框架引用
    ctx.bot            # Bot 实例
    ctx.plugin         # 当前插件实例
    ctx.matcher        # 当前匹配器实例
```

### 依赖注入

框架会自动注入以下依赖到 `self` 上，你可以在 `on_load()` 或 handler 中通过 `self.xxx` 访问：

| 属性 | 类型 | 说明 | 何时为 None |
|------|------|------|------------|
| `self.bot` | Bot 实例 | 机器人主实例 | 不会 |
| `self.db` | Database | 异步数据库操作 | 不会 |
| `self.config` | ConfigManager | 配置读写 | 不会 |
| `self.connection` | OneBotConnection | 发送消息、调用 API | 不会 |
| `self.llm` | LLMManager | 大模型对话 | 不会 |
| `self.scheduler` | APScheduler | 定时任务 | 未启用时 |
| `self.tool_registry` | ToolRegistry | Function Calling | 未启用时 |
| `self.knowledge_store` | KnowledgeStore | 知识库检索 | 未启用时 |
| `self.session_state` | SessionStateManager | 会话状态（TTL 键值存储） | 不会 |

### 会话状态（SessionState / TTL 键值存储）

借鉴 NoneBot2 的 `session.state`，提供带过期时间的会话级临时键值存储，适用于多步骤对话、表单填写等场景。

**在 handler 中通过 `ctx.session_state` 使用：**

```python
async def _handle_register(self, ctx: MatcherContext) -> str:
    step = ctx.session_state.get("step", "start")

    if step == "start":
        ctx.session_state.set("step", "waiting_name", ttl=300)
        return "请输入你的名字："

    if step == "waiting_name":
        ctx.session_state.set("name", ctx.plain_text, ttl=300)
        ctx.session_state.set("step", "waiting_age", ttl=300)
        return f"你好 {ctx.plain_text}，请输入你的年龄"

    if step == "waiting_age":
        name = ctx.session_state.get("name")
        return f"注册完成！{name}，{ctx.plain_text}岁"
```

**会话键自动隔离：** 私聊按 `private:{user_id}`，群聊按 `group:{group_id}:{user_id}`，无需手动管理。

**API 速查：**
| 方法 | 说明 |
|------|------|
| `ctx.session_state.get(key, default)` | 获取值，过期自动删除 |
| `ctx.session_state.set(key, value, ttl=0)` | 设置值，ttl=0 永不过期 |
| `ctx.session_state.delete(key)` | 删除键 |
| `ctx.session_state.clear()` | 清空当前会话 |

### 依赖注入容器（DI Container）

框架内置轻量级 DI 容器，按类型自动注入服务。插件只需声明类型注解：

```python
from qingci_plugin_sdk import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    # 声明类型注解后，框架自动注入
    # db: Database
    # llm: LLMManager
    # session_state: SessionStateManager
```

### 插件级配置（plugin_config）

插件可通过定义 `Config` 内嵌类声明配置项，框架自动从 `config.yaml` 加载：

```python
from pydantic import BaseModel
from qingci_plugin_sdk import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"

    class Config(BaseModel):
        greeting: str = "你好"
        max_length: int = 100

    async def on_load(self):
        # self.plugin_config 已自动加载
        greeting = self.plugin_config.greeting
```

对应 `config.yaml`：
```yaml
plugins:
  my_plugin:
    greeting: "Hello"
    max_length: 200
```

### 插件导出/导入（export / require）

插件间可暴露和调用服务接口：

```python
# 提供方
class ChatPlugin(PluginBase):
    name = "chat"
    async def on_load(self):
        self.export("get_history", self.get_history)

# 消费方
class MyPlugin(PluginBase):
    name = "my_plugin"
    require = ["chat"]
    async def on_load(self):
        chat = self.get_exports("chat")
        history = await chat["get_history"](user_id=123)
```

> 注意：获取导出使用 `get_exports()` 方法，`require` 仅作为类属性声明依赖（两者原本重名，已拆分）。

### 插件级中间件

每个插件可注册 handler 前置/后置钩子：

```python
class MyPlugin(PluginBase):
    name = "my_plugin"

    async def on_load(self):
        self.register_before(self._before)   # 前置钩子
        self.register_after(self._after)     # 后置钩子

    async def _before(self, matcher, ctx):
        return None  # None = 不拦截

    async def _after(self, matcher, ctx, result):
        return result  # 可修改返回值
```

### 插件元数据发现（plugin.json）

在插件目录下放置 `plugin.json`，无需导入模块即可发现插件元信息：

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "author": "YourName",
  "description": "插件描述",
  "category": "tool",
  "require": ["chat>=1.0"]
}
```

---

## 完整 API 参考

### 从 SDK 导入

```python
from qingci_plugin_sdk import (
    # 基础
    PluginBase,
    PluginStatus,
    MessageContext,
    MatcherContext,

    # 匹配器工厂
    Matcher,
    on_message,
    on_command,
    on_startswith,
    on_keyword,
    on_notice,
    on_request,

    # 权限
    Permission,
    EVERYONE,
    SUPERUSER,
    ADMIN,
    PRIVATE,
    GROUP,
    MEMBER,
    USER,
    GROUP_MEMBER,

    # 规则
    Rule,
    startswith,
    endswith,
    fullmatch,
    contains,
    regex,
    command,
    to_me,
    is_private,
    is_group,
    keyword,
    rate_limit,

    # 限流
    RateLimiter,
)
```

### 所有内置规则速查

| 函数 | 签名 | 匹配条件 |
|------|------|---------|
| `startswith` | `(prefix: str \| tuple)` | 消息以 prefix 开头 |
| `endswith` | `(suffix: str \| tuple)` | 消息以 suffix 结尾 |
| `fullmatch` | `(text: str \| tuple)` | 消息完全等于 text |
| `contains` | `(keyword: str)` | 消息包含 keyword |
| `keyword` | `(*kws: str)` | 消息包含关键词（词边界） |
| `regex` | `(pattern, flags=0)` | 正则匹配 |
| `command` | `(cmd: str \| tuple)` | 命令匹配 |
| `to_me` | `()` | @ 机器人或私聊 |
| `is_private` | `()` | 私聊 |
| `is_group` | `()` | 群聊 |
| `rate_limit` | `()` | 限流 |

### 所有内置权限速查

| 权限 | 类型 | 说明 |
|------|------|------|
| `EVERYONE` | 常量 | 所有人 |
| `SUPERUSER` | 常量 | 超级管理员 |
| `ADMIN` | 常量 | 管理员（同 SUPERUSER） |
| `PRIVATE` | 常量 | 私聊 |
| `GROUP` | 常量 | 群聊 |
| `MEMBER` | 常量 | 普通群员 |
| `USER(ids)` | 函数 | 指定用户 |
| `GROUP_MEMBER(ids)` | 函数 | 指定群成员 |

---

## 常见场景

### 发送消息到 QQ

通过 `self.connection` 可以在任意地方主动发送消息：

```python
async def on_load(self):
    # 发送私聊消息
    await self.connection.send_private_msg(user_id=123456789, message="你好！")

    # 发送群聊消息
    await self.connection.send_group_msg(group_id=987654321, message="大家好！")

    # 通用发送（自动判断类型）
    await self.connection.send_msg("group", 987654321, "通用消息")
```

> **注意**：`self.connection` 只有在 Bot 连接了 LLBot 后才能发送消息。在 handler 里直接 `return "..."` 更简单，推荐优先使用。

### 调用大模型

通过 `self.llm` 可以调用 LLM 生成回复：

```python
async def _handle_ai(self, ctx: MatcherContext) -> str:
    # 简单调用
    reply = await self.llm.chat(
        user_id=ctx.user_id,        # 用户标识（用于会话隔离）
        group_id=ctx.group_id,      # 群标识（私聊为 0）
        message=ctx.args,           # 用户输入
        system_prompt="你是一个助人为乐的助手",  # 可选，覆盖系统提示词
    )
    return reply
```

### 定时任务

通过 `self.scheduler` 可以注册定时任务：

```python
async def on_load(self):
    if self.scheduler is not None:
        # 每隔 1 小时执行
        self.scheduler.add_job(
            self._hourly_task,
            trigger="interval",
            job_id="hourly_check",
            owner=self.name,
            hours=1,
        )

        # 每天 8:00 执行
        self.scheduler.add_job(
            self._daily_task,
            trigger="cron",
            job_id="daily_report",
            owner=self.name,
            hour=8,
            minute=0,
        )


async def _hourly_task(self):
    """每小时执行的任务"""
    await self.connection.send_group_msg(
        group_id=123456,
        message="整点报时！"
    )


async def _daily_task(self):
    """每天 8:00 执行的任务"""
    await self.connection.send_group_msg(
        group_id=123456,
        message="早上好！新的一天开始了。"
    )
```

> **重要**：`self.scheduler` 可能为 `None`（如果主项目未启用调度器），使用前务必判空。

### Function Calling

如果主项目启用了 `enable_tools`，你可以注册工具让 LLM 自动调用：

```python
async def on_load(self):
    if self.tool_registry is not None:
        self.tool_registry.register(
            name="get_time",
            description="获取当前时间",
            parameters={
                "type": "object",
                "properties": {
                    "timezone_offset": {
                        "type": "number",
                        "description": "时区偏移（小时），默认 8",
                    }
                },
            },
            handler=self._tool_get_time,
        )


async def _tool_get_time(self, timezone_offset: int = 8) -> str:
    """LLM 可调用的工具"""
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=timezone_offset))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
```

### 一次性匹配器

`temp=True` 的匹配器触发一次后会自动移除，适合「等待下一条消息」的场景：

```python
self.matchers.append(
    on_message(
        rule=command("next"),
        temp=True,  # 关键：触发一次后自动移除
        priority=1,
    )(self._wait_next)
)
```

### 模块级装饰器

除了在 `on_load` 中注册，你也可以在类外面用装饰器直接注册。这种方式不需要 `self`：

```python
from qingci_plugin_sdk import on_command, MatcherContext

@on_command("status", description="查看状态")
async def status_handler(ctx: MatcherContext) -> str:
    """模块级命令处理器"""
    if ctx.bot is None:
        return "Bot 未就绪"
    status = ctx.bot.get_status()
    return f"运行状态: {'运行中' if status['running'] else '已停止'}"
```

> **区别**：模块级装饰器里只能通过 `ctx.bot` 访问依赖，不能访问 `self`。插件内注册更灵活，推荐新手使用插件内注册。

---

## 发布插件

开发完成后，把 `.py` 文件复制到 Qingci-Bot 的 `plugins/` 目录即可：

```bash
# Windows
copy plugins\my_plugin.py ..\Qingci-Bot\plugins\

# Mac / Linux
cp plugins/my_plugin.py ../Qingci-Bot/plugins/
```

重启 Bot 或通过 Web UI 插件管理页热重载，插件就会生效。

---

## 常见问题

### Q: 我改了代码，但 Bot 没变化？

A: 需要重启 Bot 或在 Web UI 的「插件管理」页点击「重载」。只改文件不会自动生效。

### Q: 插件加载报错 "PluginBase subclass not found"？

A: 检查你的类名是否和文件名一致（不是必须，但建议），以及是否继承了 `PluginBase`。

### Q: `self.scheduler` 或 `self.tool_registry` 是 None？

A: 这些是可选依赖，取决于主项目的配置。使用前务必判空：`if self.scheduler is not None:`。

### Q: 如何调试插件？

A: 在代码里加 `logger.info(...)` 打印日志，然后在 Qingci-Bot 的 Web UI「日志」页面查看输出。

### Q: 可以导入第三方库吗？

A: 可以，但要确保主项目的 Python 环境里也安装了该库。建议尽量使用 SDK 提供的能力，减少外部依赖。

### Q: 模板文件 `_template.py` 会被加载吗？

A: 不会。以 `_` 开头的文件会被自动跳过。你可以放心保留它作为参考。

### Q: 多个插件能同时响应同一条消息吗？

A: 取决于 `block` 参数。`block=True`（默认）的匹配器匹配后，后续匹配器不再执行。`block=False` 则继续。

---

## 许可

[GPL-3.0-or-later](LICENSE)