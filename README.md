# Qingci-Bot-CE 插件开发工作区

> **代码托管**：本项目以 [GitHub](https://github.com/Qingci-Bot/Plugins-SDK) 为唯一仓库；贡献与提 PR 一律以 GitHub 为准。

> 本项目底层核心代码由 [**Zhou Zhe (aka luoqingci)**](https://github.com/luoqingciya) 原创，并授予 [Qingci-Bot](https://github.com/Qingci-Bot) 组织持续开发。

> 零基础也能看懂的插件开发指南。读完这篇文档，你就能写出自己的 QQ 机器人插件。

独立于主项目的插件开发环境，包含完整的 SDK 和模板。你只需要一台电脑、一个代码编辑器，就可以开始开发插件。

本仓库是**插件协议层的唯一来源**：`PluginBase`/`Matcher`/`Permission`/`Rule`/`MessageContext` 等协议定义在这里维护，主项目 `Qingci-Bot-CE` 的 `bot/plugin/protocol/` 为薄转发（`bot/plugin/` 顶层同名文件为兼容再导出），内置插件与外部插件共用同一套 API。

> 主项目：[Qingci-Bot-CE](https://github.com/Qingci-Bot/Qingci-Bot-CE) — 基于 Python 的 QQ 机器人框架

**相关文档：**
- [项目结构规范](docs/PROJECT_STRUCTURE.md) — 目录职责与产物归属
- [编码规范](docs/CODING_STANDARDS.md) — SDK 代码组织与约定
- [变更记录](CHANGELOG.md) — 版本历史

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
  - [类型化事件（notice/request）](#类型化事件noticerequest)
  - [规则 Rule](#规则-rule)
  - [权限 Permission](#权限-permission)
  - [上下文 MatcherContext](#上下文-matchercontext)
  - [多平台插件开发（QQ / Telegram）](#多平台插件开发qq--telegram)
  - [会话阶梯（多轮交互）](#会话阶梯多轮交互)
  - [依赖注入](#依赖注入)
- [完整 API 参考](#完整-api-参考)
  - [从 SDK 导入](#从-sdk-导入)
  - [指令系统增强](#指令系统增强140)
  - [全局生命周期钩子](#全局生命周期钩子140)
  - [国际化 i18n](#国际化-i18n140)
  - [LLM 工具声明](#llm-工具声明140)
  - [插件数据目录](#插件数据目录140)
- [命令管理](#命令管理)
- [常见场景](#常见场景)
  - [发送消息](#发送消息)
  - [调用大模型](#调用大模型)
  - [定时任务](#定时任务)
  - [Function Calling](#function-calling)
  - [一次性匹配器](#一次性匹配器)
  - [模块级装饰器](#模块级装饰器)
  - [Web 管理页面](#web-管理页面register_page)
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
├── README.md                # 你现在看的文档
├── pyproject.toml           # 项目配置（包名、版本、依赖）
├── uv.lock                  # 依赖锁定文件
├── .gitignore               # Git 忽略规则
├── LICENSE                  # GPL-3.0 许可证
├── qingci_plugin_sdk/       # 插件 SDK（零外部依赖，纯 Python；插件协议层的唯一来源）
│   ├── __init__.py          # 统一导出所有 API
│   ├── base.py              # PluginBase 插件基类（旧式 on_message/on_notice/on_request 已弃用）
│   ├── context.py           # MessageContext 消息上下文（主项目 dispatcher 转发同一类型）
│   ├── events.py            # 类型化事件（notice/request 事件模型 + 解析工厂）
│   ├── matcher.py           # Matcher 匹配器 + 工厂函数
│   ├── rule.py              # Rule 规则系统 + 内置规则
│   ├── permission.py        # Permission 权限系统 + 内置权限
│   ├── ratelimit.py         # RateLimiter 限流器
│   ├── session.py           # 会话阶梯（多轮交互）：Session + Pause/Finish/Reject 异常
│   ├── i18n.py              # I18n 国际化翻译器
│   ├── llm_tool.py          # @llm_tool 插件级 LLM 工具声明
│   └── paths.py             # app_root 路径解析 + data_root 覆盖钩子（供 data_dir 使用）
└── plugins/                 # 你的插件源码都放在这里
    └── _template/           # 完整开发模板（以 _ 开头，不会被加载）
        └── __init__.py
```

> 最小示例插件已迁移至独立仓库 [Qingci-Bot/hello](https://github.com/Qingci-Bot/hello)（仓库根即插件源码），可在插件市场安装，也可作新仓库模板。

> **提示**：以 `_` 开头的目录不会被 Qingci-Bot 自动加载，所以 `_template/` 放在这里很安全，不会影响运行。

---

## 核心概念

### 命名规范

写插件之前，先了解命名规则。不遵守的话插件无法加载。

| 项目 | 规范 | 正确示例 | 错误示例 |
|------|------|---------|---------|
| 目录名 | 小写英文 + 下划线，与 `name` 一致 | `chat`、`my_plugin` | `MyPlugin`、`_test`、`插件` |
| 入口文件 | 目录下的 `__init__.py` | `chat/__init__.py` | 其他模块名 |
| 类名 | `{Name}Plugin` 帕斯卡命名 | `ChatPlugin`、`HelloPlugin` | `chat`、`my_plugin` |
| `name` 属性 | 小写英文 + 下划线，唯一标识 | `"chat"`、`"my_plugin"` | `"MyPlugin"`、`"我的插件"` |

**四条硬性规则（违反会报错）：**

1. **目录名不能以 `_` 开头** — `_template/`、`__init__.py` 会被跳过，不会被加载
2. **一个插件只能有一个插件类** — 每个 `__init__.py` 最多定义 1 个 `PluginBase` 子类
3. **`name` 不能跟其他插件重名** — 每个插件的 `name` 是唯一标识
4. **插件类必须直接定义在 `__init__.py` 中** — 不能从其他子模块 `import` 进来

> **建议**：目录名和 `name` 保持一致，类名用 `{Name}Plugin` 格式。这样无论是读代码还是管理插件，一眼就能对得上。

### 目录结构要求

框架通过扫描 `plugins/` 目录识别插件。**目录型插件**（推荐）和**文件型插件**（兼容）的判断规则：

| 形态 | 识别条件 | 入口 |
|------|----------|------|
| 目录型 | 目录内存在 `__init__.py` **或** `plugin.json` | `__init__.py`（必须含 `PluginBase` 子类） |
| 文件型 | `plugins/<name>.py` | 文件本身 |

**同名优先**：若 `plugins/chat/` 和 `plugins/chat.py` 同时存在，目录型优先，文件型被忽略。

**目录型插件结构：**

```
plugins/my_plugin/          # 目录名 = 插件名（不能以 _ 或 . 开头）
├── __init__.py              # 必需：插件入口，含 PluginBase 子类
├── plugin.json              # 可选：元数据（替代类属性 name/version/author 等）
├── requirements.txt         # 可选：Python 第三方依赖（主项目自动安装，见常见问题）
├── utils.py                 # 可选：插件内部模块
└── web/                     # 可选：Web 管理页面静态文件
    ├── index.html           # 入口页面（register_page 自动加载）
    ├── style.css
    └── app.js
```

**硬性要求：**
- 目录名不能以 `_` 或 `.` 开头，否则跳过加载
- `__init__.py` 必须存在，且其中定义**恰好 1 个** `PluginBase` 子类
- 插件类必须直接定义在 `__init__.py` 中，不能从子模块 `import` 导入
- 若 `__init__.py` 不存在但 `plugin.json` 存在，目录被识别为插件但加载会失败（缺少入口）
- 其他 `.py` 文件（如 `utils.py`）可自由存放，不会被解析为独立插件

### 插件基类 PluginBase

所有插件都必须继承 `PluginBase`，并实现 `on_load()` 和 `on_unload()` 两个方法。

```python
from qingci_plugin_sdk import PluginBase, PluginStatus


class MyPlugin(PluginBase):
    # ===== 必填 =====
    name = "my_plugin"  # 插件唯一标识

    # ===== 可选 =====
    version = "1.0.0"  # 版本号
    author = "YourName"  # 作者
    description = "我的插件"  # 简介
    category = "tool"  # 分类：chat / admin / tool / fun / 自定义
    require = []  # 依赖的其他插件，支持 PEP 440 版本约束（如 "chat>=1.0,<2.0"）

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
require = ["chat"]  # 无版本约束
require = ["chat>=1.0,<2.0"]  # 依赖 chat 1.x 版本
require = ["admin>=1.1"]  # 依赖 admin 1.1 及以上
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
plugin.status  # PluginStatus.LOADED / DISABLED / ERROR 等
plugin.enabled  # bool，向后兼容：LOADING/LOADED 为 True
```

| 状态 | 值 | 说明 |
|------|------|------|
| `LOADING` | `"loading"` | 正在加载 |
| `LOADED` | `"loaded"` | 已加载，正常运行 |
| `DISABLED` | `"disabled"` | 已禁用，跳过事件分发 |
| `ERROR` | `"error"` | 加载/运行出错 |
| `UNLOADING` | `"unloading"` | 正在卸载 |

> **旧式回调已弃用**：`on_message(ctx)` / `on_notice(event)` / `on_request(event)` 这三个重写式回调标记为 deprecated，仅向后兼容旧插件。新插件请使用 Matcher（`on_message(rule=...)` / `on_command(...)` / `on_notice(...)` / `on_request(...)` 装饰器），见下一节「匹配器 Matcher」。

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
    self.matchers.append(on_command("ping", priority=1)(self._handle_ping))

    # 方式2: 模块级装饰器（在类外面写）
    # 见下方「常见场景」章节
```

**匹配器参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `rule` | `Rule` | `None` | 额外的匹配规则 |
| `permission` | `Permission` | `EVERYONE` | 权限要求（`on_notice`/`on_request` 不支持） |
| `priority` | `int` | `1` | 优先级，越小越先执行 |
| `block` | `bool` | `True` | 匹配后是否阻止后续匹配器 |
| `temp` | `bool` | `False` | 是否一次性（触发后自动移除） |
| `description` | `str` | `""` | 功能描述（显示在 `/help` 中；`on_notice`/`on_request` 不支持） |

> `disabled` 不是工厂参数，而是 `Matcher` 字段（见 [命令管理](#命令管理)），通过 WebUI 禁用单条命令时设置。

### 类型化事件（notice/request）

`on_notice` / `on_request` handler 可通过参数注解注入**类型化事件对象**，字段带类型、有 IDE 补全，无需再手撕 dict：

```python
from qingci_plugin_sdk import (
    GroupIncreaseNotice,  # 群成员增加
    GroupBanNotice,  # 群禁言
    GroupRequestEvent,  # 加群请求
    FriendRequestEvent,  # 加好友请求
)


@on_notice()
async def on_group_increase(ctx: MatcherContext, event: GroupIncreaseNotice) -> str:
    return f"欢迎 {event.user_id}（由 {event.operator_id} 操作）入群 {event.group_id}"


@on_request()
async def on_group_request(ctx: MatcherContext, event: GroupRequestEvent) -> bool:
    # 返回 bool 表示审批结果（True 同意 / False 拒绝）
    return event.sub_type == "add"
```

**内置事件模型：**

| 事件 | 模型 | 关键字段 |
|------|------|----------|
| 群成员增加 | `GroupIncreaseNotice` | `operator_id` |
| 群成员减少 | `GroupDecreaseNotice` | `operator_id` |
| 群禁言 | `GroupBanNotice` | `operator_id`, `duration` |
| 群管理员变动 | `GroupAdminNotice` | - |
| 群消息撤回 | `GroupRecallNotice` | `operator_id`, `message_id` |
| 好友消息撤回 | `FriendRecallNotice` | `message_id` |
| 好友添加 | `FriendAddNotice` | - |
| 群文件上传 | `GroupUploadNotice` | `file` |
| 戳一戳 | `PokeNotice` | `target_id` |
| 加群请求 | `GroupRequestEvent` | `group_id`, `comment`, `flag` |
| 加好友请求 | `FriendRequestEvent` | `comment`, `flag` |

**特性：**
- 未知 `notice_type` 回退通用基类 `NoticeEvent`/`RequestEvent`（通用字段仍类型化）
- 数值字段安全转换（字符串 `"123"` 自动转 int，非法值回退默认，不抛异常）
- 原始事件保留在 `event.raw_event`（dict），旧用法 `ctx.raw_event` 不受影响
- 手动解析：`parse_notice_event(raw)` / `parse_request_event(raw)` / `parse_event(post_type, raw)`

> 类型化事件用 dataclass 实现，零依赖；与 pydantic 相比不做运行时强校验，但字段类型与补全体验一致。

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
| `SUPERUSER` | 超级管理员（唯一，config 中 `bot.super_admin` 的平台无关用户 ID） |
| `ADMIN` | 普通管理员（config 中 `bot.admin_users` 列表里的平台无关用户 ID；超级管理员自动继承） |
| `PRIVATE` | 仅限私聊 |
| `GROUP` | 仅限群聊 |
| `MEMBER` | 普通群员（与 EVERYONE 等价） |
| `USER(id)` | 指定用户可用（ID 支持数字或字符串，如 QQ 号 / Telegram 用户 ID） |
| `GROUP_MEMBER(id)` | 指定群成员可用 |

**权限组合**：

```python
# 仅管理员私聊
permission = SUPERUSER & PRIVATE

# 管理员或指定用户（数字/字符串 ID 均可）
permission = SUPERUSER | USER(123456789)

# 指定用户 123456 在私聊中
permission = USER("123456") & PRIVATE
```

**权限标签（label）：** 每个 `Permission` 带英文标识标签用于展示。内置权限的 label 为其枚举名（`SUPERUSER`/`ADMIN`/`EVERYONE` 等），组合权限自动生成组合标签（如 `(SUPERUSER & PRIVATE)`）。用 `describe_permission(perm)` 获取任意权限的标签；未标注的自定义权限返回 `CUSTOM`。主项目 Web 命令管理界面再将标签映射为中文（超级管理员/管理员/所有人等）。

### 上下文 MatcherContext

handler 函数接收的 `ctx` 参数包含了当前消息的所有信息：

```python
async def handler(ctx: MatcherContext) -> str:
    # 发送者信息
    ctx.user_id  # 发送者 ID (str | int，v11 为数字 / v12 为字符串)
    ctx.sender_name  # 发送者昵称 (str)
    ctx.group_id  # 群号，私聊时为空字符串 (str | int)

    # 消息内容
    ctx.plain_text  # 纯文本消息 (str)
    ctx.raw_message  # 可读原始文本（v12 下为 alt_message 语义）(str)
    ctx.images  # 图片 URL/file_id 列表 (list[str])

    # 命令解析（由 command/startswith 规则自动填充）
    ctx.command  # 匹配到的命令名 (str)
    ctx.args  # 命令参数 (str)

    # 正则匹配（由 regex 规则自动填充）
    ctx.match  # re.Match 对象

    # 状态
    ctx.is_at_bot  # 是否 @ 了机器人 (bool)
    ctx.message_type  # "group" 或 "private" (str)

    # 来源平台（多平台适配器，由框架在事件入口注入）
    ctx.platform  # 来源平台标识："onebot" / "telegram" / ...（默认 "onebot"）

    # 原始事件
    ctx.raw_event  # OneBot 原始事件 dict

    # 框架引用
    ctx.bot  # Bot 实例
    ctx.plugin  # 当前插件实例
    ctx.matcher  # 当前匹配器实例

    # 会话阶梯（多轮交互）
    ctx.session  # Session 对象：pause/finish/reject/send 控制多轮流程
```

### 多平台插件开发（QQ / Telegram）

内核统一采用 **OneBot 12 事件模型**，QQ（OneBot 11/12 协议端）与 Telegram 的事件在入口由各自适配器归一化为同一套内部事件，因此**插件对来源平台完全无感知**——同一份插件代码在 QQ 和 Telegram 实例上零改动即可运行，无需任何平台分支。

**为什么一样：**

- 插件 API 一致：`PluginBase` / `Matcher` / `Permission` / `Rule` / `MessageContext` 与平台无关
- 事件模型一致：`type` / `detail_type` / `{type, data}` 消息段，媒体以 `file_id` 引用
- 发送一致：`send_msg` / `send_group_msg` / `send_private_msg` 接受 v12 段数组，回复按 `ctx.platform` 自动路由回对应适配器
- 权限一致：`super_admin` / `admin_users` 等以平台无关字符串 ID 配置

**平台差异对照：**

| 维度 | QQ（OneBot 11/12） | Telegram |
|------|--------------------|----------|
| 标准 notice 事件 | 完整（撤回/禁言/poke/好友添加/上传等） | 仅成员进出群、管理员变更被归一化 |
| 平台特有扩展事件 | 无 | `message_edited` / `callback_query` / `message_reaction`（用 `on_notice()` 消费） |
| 群聊触发 | 默认直接响应 | 需 `@Bot` 提及（at 触发模式），私聊天然放行 |
| 媒体段映射 | `face`/`record` 等 QQ 段 | `photo→image`、`voice→voice`、`video→video` |
| 回调按钮 | 无 | `callback_query` 需 `call_api("answer_callback_query")` 应答 |
| 发送者字段 | `nickname`/`card` | `first_name`/`username` |

**Telegram 特有扩展事件**（QQ 无对应事件，均以扩展 notice `detail_type` 承载，插件用 `on_notice()` 消费）：

| detail_type | 说明 | SDK 类型化事件 |
|-------------|------|----------------|
| `message_edited` | 消息被编辑（携带新文本 `alt_message` 与 v12 段数组，不触发消息回复） | `MessageEditedEvent` |
| `callback_query` | 内联按钮回调（携带 `data` / `callback_query_id`，可 `call_api("answer_callback_query")` 应答） | `NoticeEvent` |
| `message_reaction` | 消息表情反应（新/旧表情列表，`sub_type` 区分 add/remove/change） | `NoticeEvent` |

**实践建议：**

- 写**通用插件**时只依赖 v12 标准事件与消息段，QQ / Telegram 直接通用
- 只有做平台特有功能（如监听消息编辑、内联按钮回调）时才用扩展事件，并建议用 `ctx.platform` 判断来源，避免在 QQ 上误触发：

```python
from qingci_plugin_sdk import on_notice, MatcherContext, MessageEditedEvent


@on_notice()
async def on_edited(ctx: MatcherContext, event: MessageEditedEvent) -> str | None:
    if ctx.platform != "telegram":
        return None  # 仅 Telegram 有消息编辑事件
    return f"你刚刚把消息改成了：{event.alt_message}"
```

### 会话阶梯（多轮交互）

用 `ctx.session` 实现声明式的多轮对话：handler 不再"一次事件一次回复"，而是可以挂起等待用户下一条消息，逐轮收集信息后结束。适合问卷、配置向导、游戏对局等场景。

```python
from qingci_plugin_sdk import PauseException, RejectException


@on_command("wizard")
async def wizard(ctx: MatcherContext):
    step = getattr(ctx.session, "step", "ask_name")
    if step == "ask_name":
        ctx.session.step = "ask_age"  # 跨轮状态
        await ctx.session.pause("请输入你的名字：")  # 挂起，等待下一条消息

    if step == "ask_age":
        ctx.session.name = ctx.plain_text
        ctx.session.step = "done"
        await ctx.session.pause(f"你好 {ctx.session.name}，请输入你的年龄：")

    ctx.session.age = ctx.plain_text
    await ctx.session.finish(f"向导完成：{ctx.session.name}，{ctx.session.age}岁")
```

**控制流 API：**

| 方法 | 行为 |
|------|------|
| `await ctx.session.send(text)` | 发送文本，不结束（handler 可继续执行） |
| `await ctx.session.pause(text)` | 发送文本并挂起，下一条同会话消息续接同一 handler（跳过命令前缀规则） |
| `await ctx.session.finish(text)` | 发送文本并结束阶梯，不再续接 |
| `await ctx.session.reject(text)` | 发送文本，拒绝当前输入并继续等待（可做输入校验） |

**特性：**
- Session 实例在阶梯期间跨轮复用：`ctx.session.任意属性 = 值` 可在多轮之间保留
- 阶梯默认 300 秒超时，超时后下一条消息不再续接；插件卸载/禁用时自动清理
- 提示文本走主动发送通道；handler 正常 `return` 的文本走回复通道
- 阶梯按会话隔离（私聊按用户、群聊按 `群号+用户`），不同用户互不干扰

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
| `self.event_bus` | EventBus | 跨插件事件总线（发布-订阅） | 不会 |

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
        self.register_before(self._before)  # 前置钩子
        self.register_after(self._after)  # 后置钩子

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

### Web 管理页面（register_page）

插件可注册自带的 Web 管理页面，入口自动显示在「插件管理」页面的插件卡片上，点击后右侧滑出抽屉 iframe 加载。

```python
class MyPlugin(PluginBase):
    name = "my_plugin"

    async def on_load(self):
        # 注册管理页面（static_dir 可选，默认自动探测插件目录下的 web/ 子目录）
        self.register_page("群排行", icon="📊", static_dir="/path/to/web/dist")
        self.register_page("成员管理", icon="👤")
```

**参数说明：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 页面标题，显示在按钮上 |
| `icon` | `str` | 图标字符，可选，默认 `◇` |
| `static_dir` | `str` | 静态文件目录的绝对路径，可选。省略时自动探测插件 `__init__.py` 同级的 `web/` 目录 |

**推荐目录结构：**
```
plugins/my_plugin/
├── __init__.py
├── plugin.json
└── web/               # ← register_page 自动探测此目录
    ├── index.html      # 入口页面
    ├── style.css
    └── app.js
```

**静态文件挂载：** 框架自动将 `web/` 目录挂载到 `/api/plugin-data/{plugin_name}/`，前端通过 iframe 加载。插件页面需预构建为纯静态 HTML/CSS/JS，不依赖框架前端构建链。

### 插件级 Web API（register_api）

插件可注册 HTTP 接口（管理页面后端、数据查询等），主项目统一挂载到 `/api/plugin-web/{plugin_name}/{path}`，鉴权对齐主项目 API 体系（`X-API-Key`），无需引入独立服务。

```python
from fastapi.responses import JSONResponse


class MyPlugin(PluginBase):
    name = "my_plugin"

    async def on_load(self):
        # 简单 JSON 接口：返回 dict 自动序列化
        self.register_api("ranking", self._api_ranking, methods=["GET"], description="群排行")
        # 上传/复杂场景：直接返回 Response 对象
        self.register_api("backup", self._api_backup, methods=["POST"])
        # 自动带状态码：返回 (data, status) 二元组
        self.register_api("members/update", self._api_member_update, methods=["POST"])

    async def _api_ranking(self, request):
        # request 为主项目 HTTP 请求对象（FastAPI Request）：request.query_params / await request.json() 等
        return {"ranking": [1, 2, 3]}

    async def _api_backup(self, request):
        return JSONResponse({"ok": True})
```

**handler 契约：**
- 参数：`request`（主项目 HTTP 请求对象，可读 `query_params` / `headers`、`await request.json()` 取 JSON body、`await request.form()` 取上传文件）
- 返回值：`Response` 对象原样返回；`(data, status_code)` 二元组按 JSON 序列化并指定状态码；`dict` / `list` / `str` 自动 JSON 序列化

**参数说明：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 相对路径（固定字面路径，不含 `{id}` 动态段；动态取值经 query 参数传递），如 `ranking`、`content-safety/terms/add` |
| `handler` | `callable` | 处理函数（见上方契约） |
| `methods` | `list[str]` | HTTP 方法列表，默认 `["GET"]` |
| `description` | `str` | 接口描述（调试/文档用） |

> 插件热重载/卸载后路由自动指向新实现或返回 404，无需重启服务。前端页面（`register_page`）可通过 `/api/plugin-web/{plugin_name}/...` 直接调用接口。

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
    describe_permission,
    # 规则
    Rule,
    startswith,
    endswith,
    fullmatch,
    contains,
    regex,
    command,
    subcommand,
    to_me,
    is_private,
    is_group,
    keyword,
    rate_limit,
    # 限流
    RateLimiter,
    # i18n 国际化
    I18n,
    # LLM 工具声明
    llm_tool,
    LlmToolSpec,
)
```

#### 指令系统增强（1.4.0）

`on_command` 现支持别名、子指令与类型化参数：

```python
# 别名：/help /帮助 /h 都触发
on_command("help", aliases=("帮助", "h"))(handler)

# 子指令：/admin ban user 路由到 ban_handler
on_command(
    "admin",
    subcommands={
        "ban": ban_handler,
        "unban": unban_handler,
    },
)(admin_handler)

# 类型化参数：/weather Beijing 3 -> city="Beijing", days=3（注入 handler 形参）
on_command("weather", args_schema={"city": str, "days": int})


async def weather(ctx, city: str = "", days: int = 1) -> str:
    return f"{city}: {days} 天预报"
```

#### 全局生命周期钩子（1.4.0）

插件可覆写以下钩子参与 Bot 生命周期（默认空实现）：

```python
class MyPlugin(PluginBase):
    async def on_startup(self):  # 启动完成（所有插件加载后）
        ...
    async def on_shutdown(self):  # 停止时（on_unload 之前）
        ...
    async def on_bot_connect(self):  # QQ 会话连接/重连
        ...
    async def on_metaevent(self, event: dict) -> bool | None:  # 元事件，返回 True 表示已消费
        ...
```

#### 国际化 i18n（1.4.0）

插件基类自动注入 `self.i18n` 与 `self._ = self.i18n.t`。翻译文件约定
`<插件模块同级>/i18n/<locale>.json`：

```json
{ "hello": "你好，{name}" }
```

```python
self._("hello", name="世界")  # -> "你好，世界"
```

#### LLM 工具声明（1.4.0）

用 `@llm_tool` 装饰器把函数暴露为 LLM 可调用的工具（模块级或类方法均可，
PluginManager 加载时自动收集）：

```python
from qingci_plugin_sdk import llm_tool


@llm_tool(name="get_time", description="获取当前时间")
async def get_time() -> str:
    return "2026-08-14 12:00:00"
```

#### 插件数据目录（1.4.0）

`self.data_dir` 返回插件专属数据目录（`app_root()/data/plugins/<name>/`，
自动创建，卸载不删除），用于持久化缓存、导出文件等。

> **实例隔离（1.6.0+）**：主项目加载 SDK 式插件时会调用 `paths.set_data_root()`
> 将数据根重定向到当前实例（`instances/<name>/data/`），此时 `data_dir` 为
> `instances/<name>/data/plugins/<name>/`。`paths.data_root()` 可查询当前数据根；
> 独立开发时未调用 `set_data_root()`，行为保持 `app_root()/data` 不变。

### 所有内置规则速查

| 函数 | 签名 | 匹配条件 |
|------|------|---------|
| `startswith` | `(prefix: str \| tuple[str, ...])` | 消息以 prefix 开头 |
| `endswith` | `(suffix: str \| tuple[str, ...])` | 消息以 suffix 结尾 |
| `fullmatch` | `(text: str \| tuple[str, ...])` | 消息完全等于 text |
| `contains` | `(keyword: str)` | 消息包含 keyword |
| `keyword` | `(*kws: str)` | 消息包含关键词（词边界） |
| `regex` | `(pattern: str \| re.Pattern, flags=0)` | 正则匹配 |
| `command` | `(cmd: str \| tuple)` | 命令匹配 |
| `subcommand` | `(parent: str, sub: str)` | 子指令匹配 |
| `to_me` | `()` | @ 机器人或私聊 |
| `is_private` | `()` | 私聊 |
| `is_group` | `()` | 群聊 |
| `rate_limit` | `()` | 限流 |

### 所有内置权限速查

| 权限 | 类型 | 说明 |
|------|------|------|
| `EVERYONE` | 常量 | 所有人 |
| `SUPERUSER` | 常量 | 超级管理员（唯一，`bot.super_admin`） |
| `ADMIN` | 常量 | 普通管理员（`bot.admin_users`；超级管理员自动继承） |
| `PRIVATE` | 常量 | 私聊 |
| `GROUP` | 常量 | 群聊 |
| `MEMBER` | 常量 | 普通群员 |
| `USER(ids)` | 函数 | 指定用户 |
| `GROUP_MEMBER(ids)` | 函数 | 指定群成员 |

---

## 命令管理

多个插件可能注册同名命令（如两个插件都注册 `/help`），调度时优先级高的胜出，其余被静默覆盖。框架提供命令管理能力，可在 WebUI 中查看冲突、禁用单条命令或调整优先级。

**命令冲突检测：**

插件管理页 →「命令管理」Tab 列出所有已注册命令。冲突命令行红色高亮 + ⚠ 标记，一目了然。

**禁用单条命令：**

点击「禁用」按钮，该命令不再参与调度，但插件其余功能不受影响。相当于在不卸载插件的前提下关闭某个命令。SDK 中对应 `Matcher.disabled = True` 字段。

**调整优先级：**

直接修改表格中的优先级数字，回车生效。优先级越小越先执行，范围为 0–100。

**权限等级显示：**

「命令管理」表格新增权限列，展示每条命令对应的权限等级（如「超级管理员」「管理员」「所有人」等）。`Permission` 的 `label` 为英文标识（`EVERYONE`/`SUPERUSER`/`ADMIN`/`PRIVATE`/`GROUP`/`MEMBER`/`USER`/`GROUP_MEMBER`），组合运算（`&`/`|`/`~`）自动生成组合标签（如 `(SUPERUSER & PRIVATE)`），未标注的自定义权限经 `describe_permission()` 返回 `CUSTOM`；主项目 Web 表格将其映射为中文（超级管理员/管理员/所有人/自定义等）。SDK 提供 `describe_permission(perm) -> str` 返回权限标签，供主项目命令管理界面展示。

**API 端点：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/command/conflicts` | 列出所有命令及冲突信息 |
| PUT | `/api/command/{owner}/{command}` | 更新命令状态（`disabled` / `priority`） |

---

## 常见场景

### 发送消息

通过 `self.connection` 可以在任意地方主动发送消息（QQ 与 Telegram 通用，回复自动路由回来源平台）：

```python
async def on_load(self):
    # 发送私聊消息
    await self.connection.send_private_msg(user_id=123456789, message="你好！")

    # 发送群聊消息
    await self.connection.send_group_msg(group_id=987654321, message="大家好！")

    # 通用发送（自动判断类型）
    await self.connection.send_msg("group", 987654321, "通用消息")
```

> **注意**：`self.connection` 只有在 Bot 连接了对应平台适配器（如 QQ 的 LLBot / Telegram Bot）后才能发送消息。在 handler 里直接 `return "..."` 更简单，推荐优先使用。

### 调用大模型

通过 `self.llm` 可以调用 LLM 生成回复：

```python
async def _handle_ai(self, ctx: MatcherContext) -> str:
    # 简单调用
    reply = await self.llm.chat(
        user_id=ctx.user_id,  # 用户标识（用于会话隔离）
        group_id=ctx.group_id,  # 群标识（私聊为 0）
        message=ctx.args,  # 用户输入
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
    await self.connection.send_group_msg(group_id=123456, message="整点报时！")


async def _daily_task(self):
    """每天 8:00 执行的任务"""
    await self.connection.send_group_msg(group_id=123456, message="早上好！新的一天开始了。")
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

开发完成后，把插件目录复制到主项目 **Qingci-Bot-CE** 的插件目录即可（源码运行时为 `Qingci-Bot-CE/plugins/`；实例模式下为 `Qingci-Bot-CE/instances/<name>/plugins/`，下例以 `default` 实例为例）：

```bash
# Windows
xcopy /E /I plugins\my_plugin ..\Qingci-Bot-CE\instances\default\plugins\my_plugin

# Mac / Linux
cp -r plugins/my_plugin ../Qingci-Bot-CE/instances/default/plugins/
```

重启 Bot 或通过 Web UI 插件管理页热重载，插件就会生效。

---

## 常见问题

### Q: 我改了代码，但 Bot 没变化？

A: 需要重启 Bot 或在 Web UI 的「插件管理」页点击「重载」。只改文件不会自动生效。

### Q: 插件加载报错 "PluginBase subclass not found"？

A: 检查你的类名是否和目录名一致（不是必须，但建议），以及是否继承了 `PluginBase`，且插件类直接定义在 `__init__.py` 中。

### Q: `self.scheduler` 或 `self.tool_registry` 是 None？

A: 这些是可选依赖，取决于主项目的配置。使用前务必判空：`if self.scheduler is not None:`。

### Q: 如何调试插件？

A: 在代码里加 `logger.info(...)` 打印日志，然后在 Qingci-Bot 的 Web UI「日志」页面查看输出。

### Q: 可以导入第三方库吗？

A: 可以。在插件目录放置 `requirements.txt`（或在 `plugin.json` 的 `requirements` 字段）声明依赖，主项目加载插件时会自动安装到实例隔离目录（`data_root()/deps/`）并注入 `sys.path`，插件内可直接 `import`。该自动安装由主项目 `config.yaml` 的 `bot.auto_install_plugin_deps` 控制（默认开启，可关闭以降低供给链风险）。建议尽量使用 SDK 提供的能力，减少外部依赖。

> 注意区分：`requirements` 声明 **Python 包依赖**（自动安装）；类属性 `require` 声明**插件间依赖**（加载顺序与版本约束），两者不同。

### Q: 模板目录 `_template/` 会被加载吗？

A: 不会。以 `_` 开头的目录会被自动跳过。你可以放心保留它作为参考。

### Q: 多个插件能同时响应同一条消息吗？

A: 取决于 `block` 参数。`block=True`（默认）的匹配器匹配后，后续匹配器不再执行。`block=False` 则继续。

---

## 许可

[GPL-3.0-or-later](LICENSE)