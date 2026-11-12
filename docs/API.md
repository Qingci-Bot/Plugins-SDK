# API 参考

> qingci_plugin_sdk 完整导入清单与核心 API 签名，与包级 __all__ 一一对应。

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

> 上面是**常用符号**清单。完整导出见 `qingci_plugin_sdk.__all__`（当前 85 项）；
> 类型化事件见「类型化事件」章节，消息段工具（`Message` / `MessageSegment` / `parse_cq_string`）
> 见「发送富文本消息（消息段）」。

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

**help 可见性（1.13.5）：** `hidden_in_help=True` 的命令不出现在宿主 `/help` 列表（用于内部/调试命令）；`meta["aliases"]` 记录完整命令别名（`meta["hidden_in_help"]` 亦写入），供宿主 `/help` 展示与过滤。

```python
# 内部调试命令，不在 /help 显示
on_command("debug", hidden_in_help=True)(handler)
# 注册后：meta["aliases"] == ["帮助", "h"]，meta["hidden_in_help"] == True
on_command("help", aliases=("帮助", "h"), hidden_in_help=True)(handler)
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
    async def on_metaevent(self, event: dict) -> bool | None:  # 旁路通知
        ...
```

> `on_metaevent` 是**旁路通知**：每个覆写了它的插件都会收到，没有「消费掉、后续插件不再收到」的语义（宿主分发时会忽略返回值）。需要拦截事件请用 Matcher 的 `block`，需要审批加好友/加群请用 `on_request` 返回 `bool`。

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

用 `@llm_tool` 装饰器把**模块级自由函数**暴露为 LLM 可调用的工具（PluginManager
加载时自动收集）：

```python
from qingci_plugin_sdk import llm_tool


@llm_tool(name="get_time", description="获取当前时间")
async def get_time() -> str:
    return "2026-08-14 12:00:00"
```

> ⚠️ **仅用于模块级自由函数**：装饰器收集到的是原函数对象（未绑定），宿主按零参
> 调用。**不要装饰插件类方法**（`def get_time(self)`）——v1.13.4 起装饰器会拒绝
> 收集类方法并告警（运行时缺 self 会 TypeError）。插件方法请用
> `self.tool_registry.register(name=..., description=..., parameters=..., handler=self.method)`。

#### 插件数据目录（1.4.0）

`self.data_dir` 返回插件专属数据目录（`app_root()/data/plugins/<name>/`，
自动创建；宿主卸载插件默认保留该目录，仅宿主「彻底删除（purge）」时删除），
用于持久化缓存、导出文件等。

> **实例隔离（1.6.0+）**：主项目加载 SDK 式插件时会调用 `paths.set_data_root()`
> 将数据根重定向到当前实例（`instances/<name>/data/`），此时 `data_dir` 为
> `instances/<name>/data/plugins/<name>/`。`paths.data_root()` 可查询当前数据根；
> 独立开发时未调用 `set_data_root()`，行为保持 `app_root()/data` 不变。

#### 适配器与底层辅助

主项目内部与自定义适配器会用到的底层工具，插件一般不必直接调用，列出以便排查与扩展：

| 符号 | 用途 |
|------|------|
| `parse_v12_event(event)` | 按 `type`/`detail_type` 分派到具体事件模型（`parse_notice_event` / `parse_request_event` 的上层入口） |
| `translate_v11_event(event)` | v11 事件 → v12 结构（主项目 `v11_compat` 翻译层即基于此） |
| `detail_type_to_notice_type(detail)` / `notice_type_to_detail_type(t)` | `detail_type` 与 v11 `notice_type` 双向映射 |
| `SegmentType` | 段类型常量（`text` / `image` / `mention` / `reply` …），避免手写字符串 |
| `normalize_v11_segment(seg)` | 单个 v11 段 → v12 段 |
| `to_v11_segment(seg)` | 单个 v12 段 → v11 段 |
| `segments_to_v11(list)` / `segments_to_v12(list)` | 整条消息在 v11 / v12 段数组之间转换 |
| `begin_module_collection()` / `end_module_collection()` | 模块级装饰器收集器（加载器使用；嵌套安全，内部为栈） |
| `begin_tool_collection()` / `end_tool_collection()` | `@llm_tool` 收集器（同上） |
| `FinishException` / `PauseException` / `RejectException` | 会话阶梯控制流异常（`session.finish/pause/reject` 内部抛出，由框架捕获） |

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
