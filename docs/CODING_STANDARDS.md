# 编码规范

> 本文档定义 `Plugins-SDK` 的代码组织与命名约定、提交前检查与发版流程。目标是让 SDK 轻量、
> 自包含、可独立安装，同时作为插件协议层的唯一来源，与主项目 `Qingci-Bot-CE` 保持一致的行为。
> 所有新增代码必须遵守本规范。

## 1. 核心原则

- **自包含**：SDK 不得 `import bot.*`（主项目）或任何运行时外部服务，保证 `pip install -e .` 后即可独立使用。
- **协议层唯一来源**：`PluginBase`/`Matcher`/`Permission`/`Rule`/`MessageContext`/`RateLimiter` 等协议定义只存在于本仓库；主项目 `bot/plugin/protocol/` 为薄转发（`bot/plugin/` 顶层同名文件为兼容再导出）。协议行为变更（权限语义、匹配规则、基类方法）在本仓库完成，不得改主项目副本。
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
- **宿主注入的依赖统一标 `Any | None`**：`bot` / `db` / `config` / `connection` / `llm` 等由宿主实现，
  SDK 不依赖其类型，但**不能**用 `object`——`py.typed` 生效后，下游 `self.llm.chat()` 会被判
  「object 无该属性」。SDK 自身需要具体行为时先 `bot: Any = self.bot` 再使用。
- **动态属性容器用 `__getattr__` + `__setattr__` 声明**：如 `Session` 允许插件挂跨轮状态
  （`ctx.session.step = ...`）。`__getattr__` 未命中时仍抛 `AttributeError`（保住 `getattr(..., default)` 语义），
  `__setattr__` 直接转 `object.__setattr__`（运行期行为不变，仅为类型检查开洞）。
- 可选字段用 `X | None`，并在文档/示例里给出判空写法（`ctx.session` 即属此类）。

## 3. 命名约定

| 对象 | 约定 | 示例 |
|------|------|------|
| 包 / 模块 | 小写下划线 `snake_case` | `matcher.py`, `llm_tool.py` |
| 类 | 大驼峰 `PascalCase` | `PluginBase`, `MatcherContext`, `LlmToolSpec` |
| 函数 / 方法 / 变量 | 小写下划线 | `begin_module_collection`, `app_root` |
| 私有成员 | 单下划线前缀 `_` | `_collector_stack`, `_collector_lock` |
| 常量 | 全大写 | `EVERYONE`, `SUPERUSER` |
| 公开导出 | 收录进 `__init__.py` 的 `__all__` | `on_command`, `subcommand`, `llm_tool` |

## 4. 公开 API 约定

- 所有希望插件使用的符号，必须在 `qingci_plugin_sdk/__init__.py` 中导出并加入 `__all__`。
- **模块级 `__all__` 必须与包级一致**：`events.py` 等模块的 `__all__` 决定
  `from qingci_plugin_sdk.events import *` 能取到哪些名字，漏写会导致「包级能导入、模块级星号导入拿不到」。
  新增公开符号时两处同时补，并由 `tests/test_smoke.py` 的导出面断言兜底。
- 工厂函数（`on_command` 等）返回装饰器，装饰器接收 handler 返回 `Matcher`——保持这一稳定的调用形态。
- 新增能力若与主项目 `bot/plugin/protocol/` 对齐，签名与行为应保持一致；协议变更先在 SDK 发版（发布到 PyPI），主项目再升级 `pyproject.toml` 中的 PyPI 版本约束并重新锁定 `uv.lock`。
- 生命周期钩子在 `PluginBase` 上提供**默认空实现**（`on_startup`/`on_shutdown`/`on_bot_connect`/`on_metaevent`），插件按需覆写，框架无需判空。

## 5. 提交前检查

```bash
# 在 Plugins-SDK/ 目录下运行（产物留在本目录内），与 CI 一致
uv run ruff check .                      # 静态检查（配置见 pyproject.toml）
uv run ruff format --check .             # 格式检查（含所有 Markdown 里的 python 代码块）
uv run mypy qingci_plugin_sdk plugins/_template   # 类型检查（含插件模板，与 CI 一致）
uv run pytest --cov --cov-fail-under=90  # SDK 自测 + 分支覆盖率门槛（tests/ 目录）
uv build                                 # 构建 sdist + wheel；CI 的 Build / Install smoke 会守卫 wheel 内容并在干净环境安装
```

- CI 在 Python 3.10 / 3.11 / 3.12 / 3.13 / 3.14 上运行测试（`requires-python >= 3.10` 的完整声明区间），并校验 `uv.lock` 只含官方 PyPI 来源。
- 新增公开符号必须同时补 `__all__` 与 `tests/test_smoke.py` 的导出面断言。
- **当前锁定的 ruff（0.16.3）会把仓库内所有 Markdown 的 python 代码块一起格式化**，
  因此示例必须写成合法 Python；`tests/test_docs.py` 还会校验代码块语法、导入符号是否存在、
  每个包级导出是否至少在 README 中出现一次，以及 README 写死的 `__all__` 项数。
- **`main` 是受保护分支（`enforce_admins`），不能直接 push**：改动必须走 PR，等 7 项必需状态检查
  （Lint / Type、Test py3.10–3.14、Build / Install smoke）全绿后合并，再打发版 tag。
- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:`。
- 大改动同步更新 `CHANGELOG.md`（未发版内容放 `[Unreleased]` 段，发版时归入 `## [X.Y.Z]`）与 `README.md`。
- 不提交产物与缓存（见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 产物归属约定）。

## 6. 发版流程

**分发渠道只有官方 PyPI**（`https://pypi.org/project/qingci-plugin-sdk/`）：不再上传私有索引，也不再创建 GitHub Release / 挂 wheel。首版 1.15.2 已于 2026-11-11 发布；历史 Release（v1.15.1 及以前）保留，仅供主项目旧直链依赖继续解析。

1. 改 `qingci_plugin_sdk/__init__.py` 的 `__version__`——**唯一版本来源**，`pyproject.toml` 动态读取，不要另改
2. 在 `CHANGELOG.md` 写 `## [X.Y.Z] - YYYY-MM-DD` 段落（verify 作业会检查它存在）
3. **走 PR 合并到 `main`**：受保护分支不能直接 push，等 7 项必需状态检查全绿后合并（见 §5）
4. 在合并后的 `main` 上打 tag 并推送：

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z 简述"
   git push origin vX.Y.Z
   ```

5. `.github/workflows/release.yml` 自动执行：校验 tag 与 `__version__` 一致、CHANGELOG 有该段 → 测试 + 静态检查 → 构建 wheel 并守卫其内容 → 以 Trusted Publishing 上传官方 PyPI → 查 PyPI JSON API 确认制品已入库。**到此发版结束，没有 Release 作业。**

**只发 wheel，不发 sdist**：本包是纯 Python，wheel 通用；sdist 对插件开发者没有额外价值，却要多维护一份产物、多跑一次隔离构建。`uv build --wheel` 只出 wheel，PyPI 也只收这一份产物；`SHA256SUMS` 仅作构建记录留在 artifact 里，不上传。

**前置条件（一次性配置，已完成，无需任何 secret）**：
1. PyPI 账号（站点强制 2FA，需准备恢复码）；
2. 项目 `qingci-plugin-sdk` 已由首版的 **pending publisher** 自动创建，该 publisher 已转为正式 publisher，后续在项目 Settings → Publishing 维护。字段固定为：项目名 `qingci-plugin-sdk`、owner `Qingci-Bot`、仓库 `Plugins-SDK`、workflow `release.yml`、environment `pypi`；
3. GitHub 仓库已建好名为 `pypi` 的环境（workflow 与 publisher 三处必须一致）。

流水线用 `uv publish --trusted-publishing always` 走 OIDC 换取短期令牌，仓库不再保存 `QINGCI_PYPI_TOKEN` 之类的长期上传凭据。

**为什么要有前置校验**：PyPI 不允许覆盖同版本，wheel 一旦传错只能发新版本。因此「tag 与版本号不一致」「CHANGELOG 漏写」都在上传前拦截，而不是传完才发现。

**主项目同步（待办）**：主项目 `Qingci-Bot-CE` 目前仍以 GitHub Release 直链 URL + SHA256 锁定 v1.15.1。PyPI 已有 1.15.2，需把它的依赖声明改为 PyPI 版本约束（`qingci-plugin-sdk==X.Y.Z`）并重跑 `uv lock`；此后每次发版只需升级该约束。切换完成前不要删历史 Release。
