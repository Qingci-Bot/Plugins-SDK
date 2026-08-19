# 编码规范

> 本文档定义 `Plugins-SDK` 的代码组织与命名约定。目标是让 SDK 轻量、自包含、可独立安装，
> 同时作为插件协议层的唯一来源，与主项目 `Qingci-Bot-CE` 保持一致的行为。
> 所有新增代码必须遵守本规范。

## 1. 核心原则

- **自包含**：SDK 不得 `import bot.*`（主项目）或任何运行时外部服务，保证 `pip install -e .` 后即可独立使用。
- **协议层唯一来源**：`PluginBase`/`Matcher`/`Permission`/`Rule`/`MessageContext`/`RateLimiter` 等协议定义只存在于本仓库；主项目 `bot/plugin/` 为薄转发。协议行为变更（权限语义、匹配规则、基类方法）在本仓库完成，不得改主项目副本。
- **轻量**：SDK 只暴露插件开发所需 API，不承担主项目框架逻辑（调度、连接、持久化由主项目负责）。
- **零/极简依赖**：`pyproject.toml` 的 `dependencies` 保持为空或尽量少，插件开发者不应为装 SDK 引入一堆传递依赖。
- **向后兼容**：公开 API（`__all__`）变更需谨慎，破坏性改动必须同步 `CHANGELOG.md` 并提示迁移。

## 2. 类型与语法约定

- 使用 **PEP 604 联合类型**：`int | None` 而非 `Optional[int]`；`X | Y` 而非 `Union[X, Y]`（`ruff UP` 规则强制，全库已迁移）。
- 通用类型用内置泛型：`list[T]` / `dict[K, V]` / `set[T]`，不用 `typing.List`。
- forward-ref 联合（`"SomeType" | None`）：模块级使用需配合 `from __future__ import annotations`（参考 `matcher.py`）。
- 显式返回类型：公开函数/方法标注返回类型，避免静默返回 `Any`（必要时 `cast`）。
- `except` 块抛出异常时用 `raise ... from None`，消除异常链噪音。
- 模块级装饰器（`on_command`、`@llm_tool`）的收集器用 `threading.Lock` 保护，避免并发加载交错污染全局状态。
- 弃用 API（如旧式 `on_message`/`on_notice`/`on_request`）在 docstring 标注 `Deprecated` 并说明替代方式。

## 3. 命名约定

| 对象 | 约定 | 示例 |
|------|------|------|
| 包 / 模块 | 小写下划线 `snake_case` | `matcher.py`, `llm_tool.py` |
| 类 | 大驼峰 `PascalCase` | `PluginBase`, `MatcherContext`, `LlmToolSpec` |
| 函数 / 方法 / 变量 | 小写下划线 | `begin_module_collection`, `app_root` |
| 私有成员 | 单下划线前缀 `_` | `_tool_collector`, `_collector_lock` |
| 常量 | 全大写 | `EVERYONE`, `SUPERUSER` |
| 公开导出 | 收录进 `__init__.py` 的 `__all__` | `on_command`, `subcommand`, `llm_tool` |

## 4. 公开 API 约定

- 所有希望插件使用的符号，必须在 `qingci_plugin_sdk/__init__.py` 中导出并加入 `__all__`。
- 工厂函数（`on_command` 等）返回装饰器，装饰器接收 handler 返回 `Matcher`——保持这一稳定的调用形态。
- 新增能力若与主项目 `bot/plugin/` 对齐，签名与行为应保持一致；协议变更先在 SDK 发布，主项目通过 git 依赖版本锁定同步。
- 生命周期钩子在 `PluginBase` 上提供**默认空实现**（`on_startup`/`on_shutdown`/`on_bot_connect`/`on_metaevent`），插件按需覆写，框架无需判空。

## 5. 提交前检查

```bash
# 在 Plugins-SDK/ 目录下运行（产物留在本目录内）
ruff check qingci_plugin_sdk plugins   # 静态检查（配置见 pyproject.toml）
ruff format --check qingci_plugin_sdk plugins   # 格式检查
mypy qingci_plugin_sdk                # 类型检查（配置见 pyproject.toml）
pytest                                # SDK 自测（tests/ 目录）
python -m py_compile qingci_plugin_sdk/*.py   # 语法正确性兜底
```

- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:`。
- 大改动同步更新 `CHANGELOG.md`（`[Unreleased]` 段）与 `README.md`。
- 不提交产物与缓存（见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 产物归属约定）。
