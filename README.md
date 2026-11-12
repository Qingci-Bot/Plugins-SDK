# Qingci-Bot-CE 插件开发工作区

> **代码托管**：本项目以 [GitHub](https://github.com/Qingci-Bot/Plugins-SDK) 为唯一仓库；贡献与提 PR 一律以 GitHub 为准。

> **版权与授权**：本仓库（与 [Qingci-Bot-CE](https://github.com/Qingci-Bot/Qingci-Bot-CE)）原为 **[Zhou Zhe (aka luoqingci)](https://github.com/luoqingciya)** 的个人项目，版权完整、排他地归其个人所有；[Qingci-Bot](https://github.com/Qingci-Bot) 组织获永久、不可撤销的 GPLv3 使用 / 修改 / 分发许可及维权授权，负责持续维护，**不是共同版权人**。完整授权文本见 [NOTICE](./NOTICE)。

独立于主项目的插件开发环境，包含完整的 SDK 和模板。你只需要一台电脑、一个代码编辑器，就可以开始开发插件。

本仓库是**插件协议层的唯一来源**：`PluginBase`/`Matcher`/`Permission`/`Rule`/`MessageContext` 等协议定义在这里维护，主项目 `Qingci-Bot-CE` 的 `bot/plugin/protocol/` 为薄转发（`bot/plugin/` 顶层同名文件为兼容再导出），内置插件与外部插件共用同一套 API。

> 主项目：[Qingci-Bot-CE](https://github.com/Qingci-Bot/Qingci-Bot-CE) — 基于 Python 的 QQ 机器人框架

---

## 文档导航

**开发：**

- [快速上手](docs/GETTING_STARTED.md) — 环境准备、5 分钟跑通、第一个插件、项目结构
- [插件开发指南](docs/PLUGIN_GUIDE.md) — 核心概念、命令管理、常见场景（匹配器 / 权限 / 会话 / 事件总线 / LLM 工具）
- [API 参考](docs/API.md) — 完整导入清单与核心 API 签名
- [发布与常见问题](docs/PUBLISHING.md) — 插件放进主项目运行、发布流程、排障 FAQ

**参与贡献：**

- [项目结构规范](docs/PROJECT_STRUCTURE.md) — 目录职责与产物归属
- [编码规范](docs/CODING_STANDARDS.md) — 代码组织、提交前检查与发版流程
- [贡献指南](CONTRIBUTING.md) — 开发环境、提交与 PR 流程
- [安全策略](SECURITY.md) — 漏洞报告与供应链
- [变更记录](CHANGELOG.md) — 版本历史
- [PyPI 包页面](https://pypi.org/project/qingci-plugin-sdk/) — 已发布版本与 wheel（唯一分发渠道；GitHub Releases 已停用，发布说明见 CHANGELOG.md）

---

## 特性

- **协议层唯一来源**：`PluginBase` / `Matcher` / `Permission` / `Rule` / `MessageContext` 在本仓库维护，主项目薄转发，插件与主项目共用同一套 API
- **零门槛上手**：模板 + 分步指南，一台电脑、一个编辑器即可开始
- **热重载**：改代码无需重启，保存即生效
- **权限 / 规则 / 会话 / LLM 工具**：开箱即用的插件能力全家桶

## 5 分钟上手（极简版）

```bash
# 1. 获取开发工作区并安装 SDK（或直接 uv add qingci-plugin-sdk 装 PyPI 发布版）
git clone https://github.com/Qingci-Bot/Plugins-SDK.git
cd Plugins-SDK
uv venv && uv pip install -e .
```

```python
# 2. 从模板创建插件：xcopy /E /I plugins\_template plugins\hello（Windows）
#    cp -r plugins/_template plugins/hello（Mac / Linux）
# 3. 编辑 plugins/hello/__init__.py：
from qingci_plugin_sdk import PluginBase, on_command


class Plugin(PluginBase):
    name = "hello"
    version = "0.1.0"

    @on_command("hello")
    async def hello(self, ctx):
        """处理 /hello 命令"""
        await ctx.reply("你好！")
```

```bash
# 4. 把插件目录复制到主项目 Qingci-Bot-CE 的 plugins/ 下，重启即加载
```

完整步骤与多平台 / 依赖 / 调试说明见 [快速上手](docs/GETTING_STARTED.md)。

---

## 许可

[GPL-3.0-or-later](LICENSE)。

> 本仓库（Plugins-SDK）为纯 GPLv3 许可；主项目 [Qingci-Bot-CE](https://github.com/Qingci-Bot/Qingci-Bot-CE) 另依 GPLv3 第 7 条在其 NOTICE 中声明了附加条款（保留声明 / 修改版须改名 / 不得暗示背书），分发主项目时以主项目 NOTICE 为准。
>
> 所有源码文件均带 `Copyright (C) 2026 Zhou Zhe (aka luoqingci)` 与 `SPDX-License-Identifier: GPL-3.0-or-later` 声明，由 `scripts/license_headers.py --check` 在 CI 中校验；新增源码文件请运行 `--fix` 补齐。
