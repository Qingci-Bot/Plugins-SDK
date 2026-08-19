# 项目结构规范

> 本文档定义 `Plugins-SDK` 的目录职责、文件组织与产物归属约定，是结构相关变更的准绳。

## 1. 仓库定位

`Plugins-SDK` 是 `Qingci-Bot` 根目录下的**多个独立子项目之一**，与 `Qingci-Bot-CE`、`qqbot-plugin-comparison` 平级。它的定位是：

- **独立可安装的插件开发工具包**：打包为 `qingci-plugin-sdk`（源码目录 `qingci_plugin_sdk/`），供插件开发者 `pip/uv install -e .` 后直接使用。
- **插件协议层的唯一来源**：`PluginBase`/`Matcher`/`Permission`/`Rule`/`MessageContext`/`RateLimiter` 等协议定义在本仓库维护，主项目 `Qingci-Bot-CE` 的 `bot/plugin/protocol/` 为薄转发（`bot/plugin/` 顶层同名文件为兼容再导出），修改协议只需改这里。
- **插件的开发与验证环境**：`plugins/` 下内置 `hello`（最小示例）与 `_template`（完整模板），开发者复制模板即可开始写插件。
- **不依赖主项目**：SDK 自带 `MessageContext`、`Rule`、`Permission` 等定义，插件开发期无需主项目即可 import 与冒烟测试。

每个子项目独立管理自己的 `.git` 仓库与依赖；**任何子项目的运行产物不得写入根目录**，必须留在自身目录内。

## 2. 目录结构总览

```
Plugins-SDK/
├── qingci_plugin_sdk/        # 核心 SDK 包（可安装；协议层唯一来源）
│   ├── __init__.py           # 公开 API 导出（__all__）
│   ├── base.py               # PluginBase 插件基类（状态/导出/中间件/生命周期钩子/data_dir/i18n；旧式 on_message/on_notice/on_request 已弃用）
│   ├── context.py            # MessageContext 消息上下文（主项目 dispatcher 转发同一类型）
│   ├── matcher.py            # Matcher、MatcherContext、匹配器工厂（on_command 等）
│   ├── rule.py               # Rule 规则系统（command/subcommand/keyword/...）
│   ├── permission.py         # Permission 权限体系
│   ├── ratelimit.py          # RateLimiter 限流
│   ├── i18n.py               # I18n 国际化翻译器
│   ├── llm_tool.py           # @llm_tool 插件级 LLM 工具声明
│   ├── events.py             # 类型化事件模型（NoticeEvent/RequestEvent 及子类 + 解析工厂）
│   ├── session.py            # 会话阶梯（Session + Pause/Finish/Reject 控制流异常）
│   └── paths.py              # 路径解析：app_root 定位 + data_root 覆盖钩子（供 data_dir 重定向）
├── plugins/                  # 插件开发/验证环境
│   ├── __init__.py           # 包标记
│   ├── _template/            # 插件模板（_ 前缀 = 不参与加载，供复制）
│   └── hello/                # 最小示例插件
├── docs/                     # 规范文档（本文档 + CODING_STANDARDS.md）
├── pyproject.toml            # 包元数据（name/version）、构建配置、ruff/mypy 配置
├── README.md                 # 插件开发指南（面向插作者）
├── CHANGELOG.md              # 变更记录
├── LICENSE                   # GPL-3.0
├── uv.lock                   # uv 依赖锁
└── .gitignore                # 产物忽略规则
```

## 3. 各目录职责与归属原则

| 目录 | 职责边界 | 禁止放入 |
|------|----------|----------|
| `qingci_plugin_sdk/` | 所有可复用的插件 API（基类/匹配器/规则/权限/i18n/工具） | 具体业务插件、依赖主项目的代码 |
| `plugins/_template/` | 完整插件模板，供复制后改造 | 可被直接加载的业务逻辑 |
| `plugins/hello/` | 最小示例插件，演示最简用法 | 复杂功能堆积 |
| `docs/` | 规范文档 | 运行时产物 |

**依赖方向（强制）：**

```
qingci_plugin_sdk/  ──(pip install -e .)──▶  插件（plugins/ 或用户自己的目录）
```

- `qingci_plugin_sdk/` 内部模块**彼此独立可复用**，但不得反向依赖 `plugins/` 下的示例。
- 各模块不应 import 主项目（`bot.*`）——SDK 必须自包含，保证独立安装可用。

## 4. 产物归属约定

| 产物类型 | 允许位置 | 忽略规则 |
|----------|----------|----------|
| Python 缓存 | `__pycache__/`、`*.pyc` | `.gitignore` 已忽略 |
| 虚拟环境 | `.venv/` | 已忽略 |
| 安装元数据 | `*.egg-info/`、`build/`、`dist/` | 已忽略 |
| 运行时数据 | `data/`（插件 `data_dir` 运行时生成） | 已忽略 |
| 静态检查/测试缓存 | `.mypy_cache/`、`.ruff_cache/`、`.pytest_cache/`、`.coverage` | 已忽略 |
| 系统文件 | `.DS_Store`、`Thumbs.db` | 已忽略 |

> 规则：**在 `Plugins-SDK/` 目录下运行命令**（`uv pip install -e .`、ruff、冒烟测试），使缓存落在本目录内，避免污染根目录或其他子项目。

## 5. 命名约定（结构层面）

| 对象 | 约定 | 示例 |
|------|------|------|
| Python 包/模块 | 小写下划线 `snake_case` | `matcher.py`, `llm_tool.py` |
| 示例插件目录 | 小写单词 | `hello/` |
| 插件模板目录 | `_` 前缀（不参与加载） | `_template/` |
| 规范文档 | `UPPER_SNAKE.md` | `PROJECT_STRUCTURE.md`, `CODING_STANDARDS.md` |

> 详细命名与编码约定见 [CODING_STANDARDS.md](CODING_STANDARDS.md)。