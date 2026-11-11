# 贡献指南

> 本仓库是 `Qingci-Bot-CE` 的插件协议层 SDK，独立版本演进，自 1.15.2 起以官方 PyPI（`qingci-plugin-sdk`）分发。
> 代码规范见 [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md)，目录职责见
> [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。本文只讲「怎么参与」。

## 报告问题

- **功能缺陷 / 用法疑问**：提 Issue，附 SDK 版本（`qingci_plugin_sdk.__version__`）、Python 版本、最小复现片段
- **安全漏洞**：**不要**开公开 Issue，走 [SECURITY.md](SECURITY.md) 的私密渠道

## 开发环境

```bash
git clone https://github.com/Qingci-Bot/Plugins-SDK.git
cd Plugins-SDK

uv sync --extra dev          # 自动建 .venv 并安装开发依赖（加 --locked 可校验锁文件）
```

SDK 自身**没有运行时依赖**（`dependencies = []`）；`--extra dev` 装 pytest / pytest-asyncio /
pytest-cov / ruff / mypy / pre-commit。

> **锁文件来源**：CI 会拒绝含非官方索引的 `uv.lock`。若本机把 uv 默认源配成了镜像，
> 用 `uv sync --locked --default-index https://pypi.org/simple --extra dev`，
> 也不要把镜像地址写进锁文件。

## 提交前检查

与 CI 一致，缺一不可：

```bash
uv run ruff check .                                # 静态检查
uv run ruff format --check .                       # 格式检查（含 Markdown 里的 python 代码块）
uv run mypy qingci_plugin_sdk plugins/_template    # 类型检查（含插件模板）
uv run pytest --cov --cov-fail-under=90            # 测试 + 90% 分支覆盖率门槛
uv build                                           # 构建 sdist + wheel，CI 会做安装冒烟
```

CI 的测试矩阵覆盖 Python 3.10–3.14，并会校验 `uv.lock` 只含官方 PyPI 来源。

装本地钩子后，提交时自动跑 ruff 与文件规整（check-toml / check-yaml / 行尾空格 / 文件末尾换行）：

```bash
uv run pre-commit install
```

## 改动约定

- **协议行为变更先在 SDK 落地**：`PluginBase` / `Matcher` / `Rule` / `Permission` 的唯一实现在本仓库，主项目 `bot/plugin/protocol/` 是薄转发。改协议不要动主项目副本。
- **新增公开符号**：同时补 `qingci_plugin_sdk/__init__.py` 的 `__all__`、对应模块的 `__all__`，以及 `tests/test_smoke.py` 的导出面断言。
- **改了 README 的代码块**：示例必须是合法 Python——当前锁定的 ruff（0.16.3）会格式化仓库内所有 Markdown 的 python 代码块，`tests/test_docs.py` 还会校验语法、导入符号与导出项数。
- **大改动**：同步更新 `CHANGELOG.md`（未发版内容放 `[Unreleased]` 段）与 README。

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

## 提交与合并

`main` 是受保护分支（`enforce_admins` 开启），**直接 push 会被拒绝**。改动走 PR：

```bash
git switch -c feat/xxx
git push -u origin feat/xxx
gh pr create --base main --head feat/xxx --title "feat: xxx" --body "改动说明"
gh pr checks --watch          # 等 7 项必需状态检查全绿
gh pr merge --squash --delete-branch
```

7 项必需状态检查为：Lint / Type、Test (py3.10–3.14)、Build / Install smoke。合并后先
`git switch main && git pull --ff-only` 同步本地 main，再打发版 tag。

## 发版

维护者操作，流程见 [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) §6。
打 `vX.Y.Z` tag 后流水线自动校验、测试、构建 wheel、以 Trusted Publishing 上传官方 PyPI 并校验入库；不再创建 GitHub Release。

**主项目同步**：`Qingci-Bot-CE` 自 1.19.1 起已在 `pyproject.toml` 中以 PyPI 版本约束
（`qingci-plugin-sdk==X.Y.Z`）依赖本 SDK，`uv.lock` 同步锁定。SDK 发新版后，在主项目升级该版本约束
并重跑 `uv lock --default-index https://pypi.org/simple` 即可；历史 Release 仅作归档保留。

## 源码版权声明

所有 `.py` 源码文件开头都要有 Copyright 行与 `SPDX-License-Identifier`（本仓库为纯
GPLv3，不需要主项目那种「§7 附加条款见 LICENSE」行）。统一用脚本处理：

```bash
python scripts/license_headers.py --fix     # 补齐缺失声明（幂等）
python scripts/license_headers.py --check   # 检查；CI 由 tests/test_license_headers.py 调用，漏写即失败
```

脚本自动读取本仓库 LICENSE 判断是否含 GPLv3 §7 附加条款，因此与主项目共用同一份实现。

**版权归属**：本仓库与 Qingci-Bot-CE 原为 Zhou Zhe (aka luoqingci) 的个人项目，后转入
Qingci-Bot 组织维护；版权完整归个人所有，组织不是共同版权人（组织持有永久、不可撤销的
GPLv3 许可与维权授权，见 LICENSE 末尾）。源码头因此只写个人姓名；贡献者保留各自贡献的
版权，提交贡献即表示同意按 GPLv3 发布。
