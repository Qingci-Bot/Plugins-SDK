# 贡献指南

> 本仓库是 `Qingci-Bot-CE` 的插件协议层 SDK，独立版本演进、经私有索引分发。
> 代码规范见 [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md)，目录职责见
> [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。本文只讲「怎么参与」。

## 报告问题

- **功能缺陷 / 用法疑问**：提 Issue，附 SDK 版本（`qingci_plugin_sdk.__version__`）、Python 版本、最小复现片段
- **安全漏洞**：**不要**开公开 Issue，走 [SECURITY.md](SECURITY.md) 的私密渠道

## 开发环境

```bash
git clone https://github.com/Qingci-Bot/Plugins-SDK.git
cd Plugins-SDK

uv venv                      # 创建虚拟环境
uv sync --extra dev          # 安装测试/静态检查依赖
```

SDK 自身**没有运行时依赖**（`dependencies = []`），`--extra dev` 只装 pytest / ruff / mypy。

## 提交前检查

与 CI 完全一致，缺一不可：

```bash
uv run ruff check .                                # 静态检查
uv run ruff format --check .                       # 格式检查
uv run mypy qingci_plugin_sdk plugins/_template    # 类型检查（含插件模板）
uv run pytest --cov --cov-fail-under=90            # 测试 + 覆盖率门槛
```

也可以装本地钩子，提交时自动跑前两项：

```bash
uv run pre-commit install
```

## 改动约定

- **协议行为变更先在 SDK 落地**：`PluginBase` / `Matcher` / `Rule` / `Permission` 的唯一实现在本仓库，主项目 `bot/plugin/protocol/` 是薄转发。改协议不要动主项目副本。
- **新增公开符号**：同时补 `qingci_plugin_sdk/__init__.py` 的 `__all__`、对应模块的 `__all__`，以及 `tests/test_smoke.py` 的导出面断言。
- **改了 README 的代码块**：示例必须是合法 Python——`ruff format` 会格式化 Markdown 代码块，`tests/test_docs.py` 会校验语法与导入符号。
- **大改动**：同步更新 `CHANGELOG.md` 的 `[Unreleased]` 段与 README。

## 提交信息

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新增 xxx 能力
fix: 修复 xxx
docs: 文档
refactor: 重构（不改行为）
test: 测试
chore: 杂项
```

## 发版

维护者操作，流程见 [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) §6。
打 `vX.Y.Z` tag 后流水线自动校验、测试、构建、上传私有索引并创建 GitHub Release。

发版后记得同步主项目：更新 `pyproject.toml` 的 `qingci-plugin-sdk==X.Y.Z`、
`build.bat` / `build-linux.sh` 的安装命令，并重跑 `uv lock`。
