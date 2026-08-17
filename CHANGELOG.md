# 变更记录

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

版本号与主项目 `Qingci-Bot-CE` 保持同步。

## [Unreleased]

### Added

- `MessageContext` 新增 `platform` 字段（默认 `"onebot"`）：标识消息来源平台（多平台适配器基础）。宿主应用（Qingci-Bot）的多平台适配器在事件入口归一化时注入该字段，回复按其路由回对应平台；插件无需感知来源平台，一套 Matcher/Rule/Permission 逻辑天然支持所有已接入平台（`onebot`/`telegram`/...）。
- `paths.set_data_root()` / `paths.data_root()`：可写数据根目录的运行时覆盖钩子。宿主应用（Qingci-Bot）加载 SDK 式插件时通过 `set_data_root()` 将插件数据目录重定向到实例可写数据根，保证实例隔离；`base.PluginBase.data_dir` 改走 `data_root()/plugins/<name>/`（默认行为不变，仍为 `app_root()/data`）。
- **会话阶梯（多轮交互）**：新增 `Session` 对象与控制流异常（`PauseException`/`FinishException`/`RejectException`），`MatcherContext` 新增 `session` 字段。handler 内可 `await ctx.session.pause("提示")` 挂起等待同会话下一条消息续接、`finish()` 结束阶梯、`reject()` 拒绝当前输入继续等待、`send()` 发送而不结束；跨轮可复用同一 Session 实例保留自定义属性。已从包根导出（`from qingci_plugin_sdk import Session, PauseException, ...`）。
- **类型化事件**：新增 `events.py` 定义 notice/request 事件模型（`NoticeEvent`/`RequestEvent` 基类 + 9 个 notice 子类 + 2 个 request 子类）与解析工厂（`parse_notice_event`/`parse_request_event`/`parse_event`）。`MatcherContext` 新增 `event` 字段，handler 可按参数注解注入类型化事件对象（如 `event: GroupIncreaseNotice`）；字段按 OneBot 11 规范类型化，数值安全转换，未知类型回退基类。零依赖 dataclass 实现，已从包根导出。

### Changed

- **协议层唯一来源**：本仓库被确立为插件协议层（`PluginBase`/`Matcher`/`Permission`/`Rule`/`MessageContext`/`RateLimiter`）的唯一维护点；主项目 `Qingci-Bot-CE` 的 `bot/plugin/{base,matcher,permission,rule,ratelimit}.py` 与 `dispatcher.MessageContext` 改为薄转发，内置插件与外部插件共用同一套 API，不再双份维护
- 类型标注全面对齐 PEP 604：`Optional[X]`/`Union[X,Y]` 改为 `X | None`/`X | Y`（`matcher.py` 引入 `from __future__ import annotations` 支持 forward-ref 联合）
- 弃用：`PluginBase` 旧式回调 `on_message`/`on_notice`/`on_request` 标注 deprecated，新插件请改用 Matcher
- 质量：`pyproject.toml` 新增 ruff/mypy 配置（与主项目一致），存量 lint/type 问题清零
- 权限判定改用 `bot.config.bot.admin_set` 预编译集合（`super_admin` + `admin_users` 并集，O(1) 成员判断），`rule` 限流豁免同步受益；无 `admin_set` 属性的旧配置对象回退到列表判断，保持兼容

## [1.5.1] - 2026-08-16

### 新增

- `Permission` 新增 `label` 属性：内置权限（`EVERYONE`/`SUPERUSER`/`ADMIN`/`PRIVATE`/`GROUP`/`MEMBER`/`USER`/`GROUP_MEMBER`）标注可读标签，组合运算（`&`/`|`/`~`）自动生成组合标签（如 `(SUPERUSER & PRIVATE)`）。
- 新增 `describe_permission(perm) -> str`：返回权限的可读标签，未标注的自定义权限返回 `CUSTOM`，供主项目命令管理界面展示权限等级；已从包根导出（`from qingci_plugin_sdk import describe_permission`）。
- `on_message` 新增 `description` 参数（与 `on_command`/`on_startswith`/`on_keyword` 对齐），存入 `meta.description` 供 `/help` 与命令管理展示；修复插件模板中 `on_message(..., description=...)` 触发 `TypeError` 的问题。

## [1.5.0] - 2026-08-16

### 变更

- 权限细分为超级管理员与普通管理员：`SUPERUSER` 校验 `bot.super_admin`（唯一），`ADMIN` 校验 `bot.admin_users`（多个，超级管理员自动继承）；`rate_limit` 限流豁免纳入 `super_admin`。

## [1.4.1] - 2026-08-14

### 新增

- 新增规范文档：`docs/PROJECT_STRUCTURE.md`（目录职责与产物归属）、`docs/CODING_STANDARDS.md`（编码规范）、`CHANGELOG.md`。
- `.gitignore` 忽略运行时产物（`data/`）与静态检查/测试缓存（`.mypy_cache`、`.ruff_cache`、`.pytest_cache` 等）。

## [1.4.0] - 2026-08-14

> 与主项目 1.4.0 对齐，补齐 P0/P1/P2 新增能力。

### 新增

- **国际化 `I18n`**（`qingci_plugin_sdk/i18n.py`）：`PluginBase` 自动注入 `self.i18n` 与 `self._ = self.i18n.t`，支持加载 `i18n/<locale>.json` 翻译资源与模板格式化。
- **LLM 工具声明 `@llm_tool`**（`qingci_plugin_sdk/llm_tool.py`）：装饰器声明插件级 Function Calling 工具，含 `LlmToolSpec` 与线程安全收集机制。
- **全局生命周期钩子**：`PluginBase` 新增 `on_startup` / `on_shutdown` / `on_bot_connect` / `on_metaevent`（默认空实现，按需覆写）。
- **指令系统增强**：`on_command` 支持 `aliases`（别名）、`subcommands`（子指令）、`args_schema`（类型化参数注入 handler 形参）；`MatcherContext` 新增 `subcommand` 与 `parsed_args` 字段。
- **子指令规则 `subcommand(parent, sub)`**。
- **插件数据目录 `self.data_dir`**：返回 `app_root()/data/plugins/<name>/`，自动创建、卸载不删除。
- **`event_bus` 依赖引用**：供插件通过主项目事件总线做跨插件广播。
- 新增 `paths.py`（`app_root` 路径解析，供 `data_dir` 使用）。

### 变更

- 模块级 Matcher 收集改用 `threading.Lock` 保护，避免并发加载交错污染全局状态。
- 示例插件 `hello` 与模板 `_template` 更新，演示别名/子指令/类型化参数/生命周期钩子/`@llm_tool`。
- 版本号 `1.0.0` → `1.4.0`。

### 文档

- `README.md` 补充指令增强、生命周期钩子、i18n、LLM 工具、数据目录章节，更新导入参考与规则速查。

## [1.0.0] - 2026-08-11

### 新增

- 初始版本：`PluginBase` 基类、`Matcher`/`MatcherContext` 与匹配器工厂（`on_message`/`on_command`/`on_startswith`/`on_keyword`/`on_notice`/`on_request`）。
- `Rule` 规则系统（`command`/`startswith`/`keyword`/`regex`/`to_me`/`is_private`/`is_group`/`rate_limit` 等）。
- `Permission` 权限体系、`RateLimiter` 限流。
- 插件开发指南 `README.md` 与插件模板 `_template`。

[1.5.1]: https://atomgit.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.5.1
[1.5.0]: https://atomgit.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.5.0
[1.4.1]: https://atomgit.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.4.1
[1.4.0]: https://atomgit.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.4.0
[1.0.0]: https://atomgit.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.0.0