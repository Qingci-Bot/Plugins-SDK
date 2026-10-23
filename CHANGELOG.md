# 变更记录

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

SDK 独立版本演进，经私有 PyPI 索引分发（`qingci-plugin-sdk==X.Y.Z`）。

主项目 `Qingci-Bot-CE` 以精确版本号锁定（`pyproject.toml` 的依赖声明 + `build.bat` /
`build-linux.sh` 的安装命令 + `uv.lock` 三处一致），源由 `[[tool.uv.index]]` 绑定。

发版流程见 [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) §5：打 `vX.Y.Z` tag 即自动
校验、测试、构建、上传索引并创建 GitHub Release。

## [1.14.0] - 2026-10-23（弃用告警与工程化收口）

### Added

- **`CONTRIBUTING.md`**：环境搭建、与 CI 一致的提交前检查、改动约定、发版指引
- **`SECURITY.md`**：私密报告渠道（GitHub Security Advisories）、处理流程，并明确列出**有意为之的边界**（插件同进程运行、checker 异常按拒绝、`@llm_tool` 拒绝类方法等），避免这些设计被当成漏洞重复上报
- **`.github/dependabot.yml`**：开发依赖与 GitHub Actions 每周自动更新，按组提 PR 减少噪音
- **`.pre-commit-config.yaml`**：本地钩子（ruff / ruff-format / 文件规整），可选启用；`dev` extra 同步加入 `pre-commit`
- **CI 覆盖率摘要**：每次运行把各模块覆盖率写入 Summary 页，翻历史即可对比趋势（不引入外部服务）
- **测试补齐**：新增 `tests/test_base.py`（get_exports 失败分支、弃用钩子告警、register_page 探测）与 `tests/test_llm_tool.py`（类方法拒绝、收集器为栈）；`test_ratelimit` / `test_segments` / `test_rule` / `test_permission` 补边界与异常路径。覆盖率 92% → **96.5%**，测试数 219 → 257
- **文档一致性测试 `tests/test_docs.py`（36 例）**：校验 README 全部 python 代码块的语法、`from qingci_plugin_sdk import X` 的符号是否存在，以及每个包级导出是否至少在 README 中出现一次

### Changed

- **Python 3.14 纳入支持范围**：CI 测试矩阵与 `classifiers` 均补 3.14（此前只测到 3.13，而 `requires-python >= 3.10` 实际允许 3.14 运行，属未声明未验证）
- **弃用钩子覆写时记录 WARNING**：`on_message` / `on_notice` / `on_request` 此前只有 docstring 标注，插件作者运行时收不到任何信号。现于 `__init_subclass__` 检测覆写并记录 WARNING，明确「计划在 2.0 移除」；`plugins/_template` 同步移除示例覆写（模板是用户复制的第一份代码，不应示范弃用写法）
- **README 补「发送富文本消息（消息段）」章节**：`segments` 模块（`Message` / `MessageSegment` / `parse_cq_string` / v11↔v12 转换）此前是包级导出却无任何文档入口
- **README 补「适配器与底层辅助」小节**：覆盖此前从未提及的 13 个导出符号
- **README 会话阶梯示例补 `ctx.session` 判空**：该字段为 `Session | None`，原示例复制到类型检查环境即报错
- **README 补「有类型提示吗」FAQ**：说明 `py.typed`、判空原因、动态属性按 `Any` 处理
- **`docs/CODING_STANDARDS.md`**：mypy 范围含 `plugins/_template`；补「注入项必须标 `Any | None`」「模块级 `__all__` 与包级一致」两条约定；注明 README 代码块也会被 `ruff format` 处理
- **`uv.lock` 来源改为官方 PyPI**：锁文件此前在配置了清华镜像的机器上生成，40 个包全部指向镜像。已用 `uv lock --default-index https://pypi.org/simple` 重新生成（版本零变化，仅换来源），并在 CI 增加「锁文件来源检查」拦截非官方索引

## [1.13.9] - 2026-10-20（下游类型体验修复）

### Fixed

- **注入项类型标注统一为 `Any | None`**：`PluginBase.bot` / `db` / `config` / `connection` / `llm` 与 `MatcherContext.bot` 此前标为 `object | None`，而同类的 `scheduler` / `tool_registry` 等却是 `Any | None`。自 1.13.8 补了 `py.typed` 后，下游插件里 `self.llm.chat()`、`ctx.bot.get_status()` 全部被判「object 无该属性」（主项目一次报出 27 处）。SDK 自身靠 `bot: Any = self.bot` 内部转换绕过，CI 只检查本包故未暴露
- **`Session` 支持跨轮动态属性**：新增 `__getattr__` / `__setattr__`，插件可写 `ctx.session.step = "ask_age"` 这类跨轮状态而不再被 mypy 判 `attr-defined`；未设置的属性仍抛 `AttributeError`（`getattr(..., default)` 语义不变），真实方法/字段类型不受影响
- **`MessageEditedEvent` 补入 `events.__all__`**：此前只在包级 `__all__` 里，`from qingci_plugin_sdk.events import *` 取不到，与包级导出不一致；下游镜像模块级 `__all__` 时会漏掉该类
- **插件模板 `_on_group_notice` 返回值标注**：标注 `-> str` 却在「不处理的事件」分支返回 `None`，改为 `str | None`（与 handler 契约一致）

### Changed

- **CI 增加模板类型检查**：`mypy plugins/_template`。模板是用户复制的第一份代码，此前只检查 SDK 包本身，导致模板在 `py.typed` 下过不了类型检查却无人发现

## [1.13.8] - 2026-10-20（P0 缺陷修复 + P1 性能 + P2 打包与 CI）

### Added

- **PEP 561 类型标记（P2）**：新增 `qingci_plugin_sdk/py.typed` 并纳入 `package-data`。此前下游插件工程以非 editable 方式安装后，mypy 无法获取本包类型信息（退化为 `Any`）
- **完整的打包元数据（P2）**：`pyproject.toml` 补 `readme` / `authors` / `keywords` / `classifiers`（Python 3.10–3.13、`Typing :: Typed`）/ `[project.urls]`（Homepage / Repository / Issues / Changelog），并启用 PEP 639 SPDX 许可表达式（`license-files`，构建后端升至 setuptools>=77）
- **CI 构建与安装冒烟（P2）**：新增 `build` job，构建 sdist + wheel 后校验 wheel 内容（禁止 `tests/`、`plugins/` 泄漏，必须含 `py.typed`），并在干净虚拟环境安装 wheel 后导入验证

### Changed

- **版本单一来源（P2）**：`pyproject.toml` 改为 `dynamic = ["version"]`，从 `qingci_plugin_sdk.__version__` 静态读取，消除两处版本号双写漂移
- **wheel 不再打包 `tests/` 与 `plugins/`（P2）**：此前 `packages.find` 未限定范围，wheel 会把顶层 `plugins` 包（含 `_template`）装进下游 `site-packages`，与宿主插件目录同名冲突；现限定 `include = ["qingci_plugin_sdk*"]`，wheel 由 26 项降至 19 项
- **事件解析按类缓存字段类型（P1）**：`parse_notice_event` 此前每次调用都执行 `get_type_hints`（约 83µs，占单次解析 95%）。现按事件类缓存解析结果，单次解析 87µs → 约 1.4µs（实测 1 万次：871ms → 14ms）
- **`PluginBase.data_dir` 缓存目录解析（P1）**：此前每次访问都执行 `mkdir`（实测约 111µs），handler 内多次读取会拖慢消息处理。现按 (数据根, 插件名) 缓存，`set_data_root()` 切换或插件名变更时自动失效（实测 111µs → 约 0.4µs）
- **CI 重构（P2）**：改用 uv + `uv.lock` 严格安装（`UV_FROZEN=1`）；测试矩阵覆盖 3.10 / 3.11 / 3.12 / 3.13（此前仅 3.12，与 `requires-python >= 3.10` 不匹配）；新增 90% 分支覆盖率门槛；`push` 仅监听 `main` 并加 concurrency 取消，避免重复跑

### Fixed

- **限流表容量触顶时误淘汰他人（P0）**：`RateLimiter.check()` 此前在判断键是否存在之前执行淘汰，已有用户的每次调用都会驱逐一个无关用户——单个高频用户反复触发即可逐条清空整张限流表；被限流拒绝的调用同样触发淘汰。现仅在「新键写入且已触顶」时淘汰最久未活动者；内部结构改为 `OrderedDict` + `move_to_end`，淘汰由 O(n) `min()` 扫描降为 O(1) `popitem`，消除洪泛场景下的 O(n²) 退化（`max_entries <= 0` 表示不设上限）
- **`MessageContext.from_v12_event` 丢失 `sub_type`（P0）**：v12 归一化链路未给该兼容字段赋值，插件读取 `ctx.sub_type` 恒为空串（v11 链路正常）。现从事件原样读取，缺省保持空串；同时移除关于 time 字段的悬空注释
- **`PluginBase.require` 跨插件共享（P0）**：类级默认值为可变 list，任一插件执行 `self.require.append(...)` 会污染同进程其他插件类。新增 `__init_subclass__`，为未显式声明 `require` 的子类复制独立列表（显式声明的保持不变）
- **包级导出缺口（P0）**：`FriendPokeNotice` / `GroupLuckyKingNotice` / `GroupHonorChangeNotice` / `GroupCardNotice` / `GroupEssenceNotice` / `GroupSignInNotice` / `translate_v11_event` / `parse_cq_string` 未进 `qingci_plugin_sdk.__all__`，插件与适配器只能从子模块导入，违反 CODING_STANDARDS §4。现全部补入包级导出
- **模块级收集器改为栈（P0）**：`begin_module_collection` / `begin_tool_collection` 原为单槽全局变量，嵌套加载（插件在 `on_load` 内加载/重载其他插件）时内层 `end` 会丢弃外层已收集的 matcher / LLM 工具。现改为栈，`end` 仅弹出栈顶；私有变量 `_matcher_collector` / `_tool_collector` 相应改为 `_collector_stack`（非公开 API）

### Tests

- 测试数 148 → 180，分支覆盖率 86% → 92%（新增 `test_i18n.py`、`test_paths.py`，补齐 `PluginBase` 的 `register_page` / `get_exports` / 中间件去重 / 生命周期默认实现 / `enabled` 非法转移）
- 新增 10 条回归测试：限流重复调用 / 拒绝调用不误淘汰、v12 `sub_type` 透传、`require` 类间隔离、`__all__` 导出面一致性、嵌套 matcher / LLM 工具收集、事件注解缓存命中、`data_dir` 缓存与失效、`py.typed` 存在性

## [1.13.7] - 2026-09-03（keyword 单正则扫描 + 限流容量上限）

### Added

- **核心模块测试**：补齐 matcher / rule / segments / session / permission / ratelimit / context / events 的单元测试

### Changed

- **`keyword()` 多关键词单次扫描**：多关键词预编译为单条正则（否定 lookaround 表达词边界，CJK 与非 ASCII 一律视为边界，与原逐字符判定语义一致），每条消息只做一次扫描，替代逐关键词 `find` 的多遍线性开销
- **`RateLimiter` 新增 `max_entries` 容量上限**（默认 100000）：防长期运行内存无界膨胀，触顶时淘汰最早活动者

## [1.13.6] - 2026-08-23（OneBot 12 协议符合度：self_id 回退读取）

### Added

- **`MessageContext.from_v12_event` 兼容严格 v12 `self` 对象**：官方 v12 标准事件以 `self` 对象（`{platform, user_id}`）标识机器人，而 NapCat 等实现端以扁平 `self_id` 透传。现 `self_id` 缺失时自动回退读 `self.user_id`，两类实现端均可正确识别（SDK OneBot 12 协议审阅报告 P2·B1）

### Changed

- **`translate_v11_event` 行为说明注释（P3）**：v11 匿名群消息 `sub_type="anonymous"` 为 v11 特有、v12 无等价语义，保留原值仅作提示，插件应统一按 `detail_type=group` 路由；notice 事件 `id` 在 v11 无 `message_id` 时可能为空，核心按 `detail_type`/`user_id`/`group_id` 路由不受影响

## [1.13.5] - 2026-08-22（命令元信息：别名与 help 可见性）

### Added

- **`on_command` 新增 `hidden_in_help` 参数**：置 True 的命令不出现在宿主 `/help` 列表（用于内部/调试命令），`meta["hidden_in_help"]` 随之写入
- **`meta["aliases"]` 记录完整命令别名**：`on_command("ping", aliases=("p","pong"))` 后 `meta["aliases"] == ["p","pong"]`（此前只进匹配规则，宿主 `/help` 无法展示别名）

## [1.13.4] - 2026-08-22（SDK 代码审阅报告修复）

### Fixed

- **类型化事件字段类型由"源值类型"决定（P1）**：`parse_notice_event` 此前对 str 源值保持 str、其余转 int，而 dataclass 字段声明为 int（如 `target_id`）——OB12 字符串 ID 会被存成 str，插件对字段做数值比较/运算会崩；且该类型违约被测试固化（`target_id == "2"`）。现改为按 `dataclasses.fields` 目标类型归一（int/str/bool 分派），字符串 ID 正确转回 int，`MessageEditedEvent.message_id`（str 语义）保持 str；新增 `_bool` 安全转换（`"false"`/`"0"` 正确解析为 False）
- **`@llm_tool` 装饰插件方法捕获未绑定函数（P2）**：装饰器收集到的是原函数对象，宿主按零参调用会缺 self 抛 TypeError；模板插件 `_template` 此前在方法上误用 `@llm_tool`（死代码陷阱）。现装饰器对模块层类方法（qualname 含点且无 `<locals>`）拒绝收集并告警；模板删除该方法上的 `@llm_tool`，改注释引导 `tool_registry.register(handler=self.method)`
- **`on_startswith` 不剥离前导 `/`（P3）**：此前 `text.startswith(p)` 直接匹配，`/天气 北京` 无法触发 `on_startswith("天气")`（命令规则则能）。现与 `command` 对齐，匹配前剥离一个前导 `/`
- **`RateLimiter` 键类型与实参矛盾（P2，v1.13.3 已修）**：补记于上一版本

### Changed

- **`begin_tool_collection` / `end_tool_collection` 加入 `__all__` 导出**：与 `begin/end_module_collection` 对称（此前仅内部可用）
- **`on_notice` / `on_request` 弃用提示指向 Matcher 工厂**（matcher.py），消除方法名自指歧义
- **i18n 加载方式注释说明**：`PluginBase.i18n` 不会自动 `load_dir`，需插件在 `on_load` 手动加载 `data_dir/i18n`
- **Rule / Permission 异常处理注释**：checker 抛异常即拒绝/无权限（安全默认），说明有意为之

## [1.13.3] - 2026-08-22（跨协议一致性修复）

### Fixed

- **v11 notice 翻译白名单丢扩展字段**：`translate_v11_event` 对 notice 仅拷贝 `["duration","target_id","file","message_id"]`，`honor_type` / `card_new` / `card_old` / `operation` 等扩展通知字段被丢弃——同一类通知事件在 OB11 与 OB12/Telegram（原生构造携带全部字段）形状不同。现改为拷贝除已规范化结构键外的全部原始键，OB11 与其它协议端字段一致
- **`RateLimiter` 键类型与事件链矛盾**：`check(user_id: int)` 注解与 `dict[int,...]` 存储，但事件链中 `user_id` 统一为 str（三端均传 str）。现 `check` 接受 `str | int` 并按 str 存储，类型注解与实参一致（str/int 命中同一计数桶）

## [1.13.2] - 2026-08-21

### Added

- **扩展通知类型化**：`events.py` 新增 6 个扩展通知类型化事件类与 v11/v12 双向映射——`GroupLuckyKingNotice`（群红包运气王）/ `GroupHonorChangeNotice`（群荣誉变更）/ `GroupCardNotice`（群名片变更）/ `GroupEssenceNotice`（群精华消息）/ `GroupSignInNotice`（群签到）/ `FriendPokeNotice`（好友戳一戳）。NapCat / LLBot 等扩展协议端的这类通知此前回退 `NoticeEvent` 基类，插件需手撕 `raw_event`；现可 `on_notice` + 类型注解消费

## [1.13.1] - 2026-08-21

### Fixed

- **on_load 运行时注册的 on_command 子指令被静默丢弃**：`on_command` 的子指令 matcher 此前只进模块级收集器（import 阶段有效）；插件在 `on_load` 内运行时注册（收集器已关闭）时子 matcher 不返回、不附加，被静默丢弃，导致「父指令已排除子指令、子指令 matcher 又不注册」——子命令（如 `签到排行 今日`）完全不触发。现把全部子指令 matcher 挂到返回的 `parent.meta["sub_matchers"]`，宿主（Qingci-Bot-CE PluginManager）注册 parent 时按对象 id 去重展开注册（模块级场景不双份）。对所有在 on_load 内注册子命令的插件生效

## [1.13.0] - 2026-08-21（与 Qingci-Bot-CE 1.13.0 同步）

### Fixed

- **媒体段 v11 转换字段回退**：`to_v11_segment` 对 image/voice/audio/video/file 段在 v12 标准字段 `file_id` 缺失时，回退读取 `file`/`url` 字段（支持插件直接以 base64 或远程地址携带的 v12 图片段，如 shiguang `/签到` 卡图）；voice 段 v11 类型保持 `record`。修复 OneBot 11 发送链路只读 `file_id` 导致图片段丢失、只剩 caption 纯文本的问题

## [1.12.0] - 2026-08-20（与 Qingci-Bot-CE 1.12.0 同步）

版本号同步，无代码变更（主项目本次为阶段二/三落地：数据保留清理、前端 API 层、v11 翻译已在此前版本收敛进 SDK、PG 迁移加固等，不涉及协议层）。

## [1.11.0] - 2026-08-20（与 Qingci-Bot-CE 1.11.0 同步）

### Added

- **`translate_v11_event`**：OneBot 11 事件 dict -> OneBot 12 事件 dict 的统一翻译（message 含 CQ 码解析 / notice 按 sub_type 细分 / request / meta / 未知事件透传），作为 v11 <-> v12 协议映射的单一来源；`notice_type_to_detail_type` 支持 sub_type 细分（group_admin / group_ban）

### Fixed

- **`friend_decrease` 不再误映射到 `friend_recall`**：v11 无好友删除对应通知类型，移除映射避免监听撤回事件的插件收到错误语义通知
- **`Message.from_raw` 解析 CQ 码字符串**：新增 `parse_cq_string`，含 `[CQ:at,...]` 的 v11 字符串消息解析为 v12 段数组（`@` 识别不再失真）
- **`Rule.__or__` 完整还原 ctx**：左侧 checker 修改任意字段（含 `subcommand` 等）在未命中时均被还原，避免污染右侧判定
- **`Permission.__and__` 空 label 显示 `?`**：组合未命名的子权限时不再显示 `( & )`
- **`register_page` web/ 目录探测失败不再静默**：记录 debug 日志便于排查

## [1.10.1] - 2026-08-20

### Fixed

- **`parse_cq_string` 不再引用不存在的 `SegmentType.FACE`**：`face` 是 v11 专属段类型（v12 无标准 face 段），改用字符串字面量透传，修复 mypy CI 报错

## [1.10.0] - 2026-08-20（与 Qingci-Bot-CE 1.10.0 同步）

版本号同步，无代码变更（主项目本次为安全加固与稳定性修复，不涉及协议层）。

## [1.9.4] - 2026-08-19（与 Qingci-Bot-CE 1.9.4 同步）

版本号同步，无代码变更（主项目本次为安全与稳定性修复，不涉及协议层）。

## [1.9.3] - 2026-08-19（与 Qingci-Bot-CE 1.9.3 同步）

版本号同步，无代码变更（主项目本次为插件卸载修复，不涉及协议层）。

## [1.9.2] - 2026-08-19（与 Qingci-Bot-CE 1.9.2 同步）

### Changed

- **示例插件 `hello` 迁移至独立仓库 [Qingci-Bot/hello](https://github.com/Qingci-Bot/hello)**：仓库根即插件源码，演示插件市场「索引仓库」模型（市场只登记元数据与 `source` 地址）；`plugins/` 下仅保留 `_template/` 模板，文档同步更新。

## [1.9.1] - 2026-08-19（与 Qingci-Bot-CE 1.9.1 同步）

### Changed

- **文档同步（主项目结构重构）**：协议层归属描述对齐主项目 `Qingci-Bot-CE` 的新结构——薄转发位于 `bot/plugin/protocol/` 子包，`bot/plugin/` 顶层同名文件为兼容再导出（README / docs/PROJECT_STRUCTURE / docs/CODING_STANDARDS 同步）。

## [1.9.0] - 2026-08-19（与 Qingci-Bot-CE 1.9.0 同步）

### Added

- **`PluginBase.register_api` 插件级 Web API 注册**：插件可在 `on_load` 中注册 HTTP 接口（path / handler / methods / description），由主项目挂载到 `/api/plugin-web/{插件名}/{path}` 并提供鉴权与返回类型归一化（`Response` 原样 / `(data, status)` 二元组 / dict 自动 JSON 序列化）；handler 接收主项目 HTTP 请求对象，支持读取 query / JSON body / 上传文件。配合主项目新增的插件 Web API 机制（见 Qingci-Bot-CE 变更记录）。

## [1.8.0] - 2026-08-18（与 Qingci-Bot-CE 1.8.0 同步）

### Added

- **`MessageEditedEvent` 类型化事件**：`parse_notice_event` 将 `detail_type=message_edited` 解析为 `MessageEditedEvent`（携带 `message_id`/`alt_message`/`message` 段数组/`is_at_bot`），承载 Telegram 编辑消息扩展事件；解析器字段处理兼容 str/bool 类型（`message_id`/`alt_message`/`is_at_bot` 原样保留，不再强制转 int），未知 `detail_type` 仍安全回退 `NoticeEvent` 基类
- **OneBot 12 消息段抽象（`segments.py`）**：新增 `SegmentType` 常量、`MessageSegment` 工厂（`text`/`mention`/`mention_all`/`image`/`voice`/`audio`/`video`/`file`/`reply`/`location`）、`Message` 容器（纯文本提取/双模嗅探），以及 v11↔v12 段双向转换（`normalize_v11_segment`/`to_v11_segment`/`segments_to_v11`/`segments_to_v12`），为 OneBot 12 内核迁移提供统一消息表达。
- **v12 事件解析**：`parse_event` / `parse_notice_event` / `parse_request_event` 同时接受 v11（`notice_type`）与 v12（`detail_type`）事件 dict，v12 `detail_type` 自动映射回 v11 命名空间，插件侧事件类保持不变。

### Changed

- **权限函数支持字符串 ID**：`USER` / `GROUP_MEMBER` 参数类型由 `int` 放宽为 `int | str | list[int | str]`，内部归一化为字符串比较（OneBot 12 事件中 `user_id`/`group_id` 均为字符串，原实现仅接受 `int` 导致 Telegram 等平台权限匹配失败）；context 侧同样转字符串，保证跨平台 ID 语义一致。
- **`Message.from_raw` 修复 v12 reply 段误归一化**：reply 段在 v11（`data.id`）与 v12（`data.message_id`）语义不同，现改为仅 `at`/`at_all`/`record`/`face`/`forward` 强制 v11 嗅探，reply 按字段判别（含 `id` 且无 `message_id` 才视为 v11）。

## [1.6.0] - 2026-08-17

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

[1.6.0]: https://github.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.6.0
[1.5.1]: https://github.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.5.1
[1.5.0]: https://github.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.5.0
[1.4.1]: https://github.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.4.1
[1.4.0]: https://github.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.4.0
[1.0.0]: https://github.com/Qingci-Bot/Plugins-SDK/releases/tag/v1.0.0