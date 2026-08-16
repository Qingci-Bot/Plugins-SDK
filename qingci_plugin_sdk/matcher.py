"""匹配器系统 — 插件 SDK 独立版本

核心概念：
- Matcher: 绑定 handler + rule + permission + priority 的匹配单元
- MatcherContext: 增强版 MessageContext，注入 bot/plugin/matcher 引用
- 工厂函数: on_message / on_command / on_startswith / on_keyword / on_notice / on_request
"""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, fields, replace
from typing import TYPE_CHECKING, Any

from .context import MessageContext
from .permission import EVERYONE, Permission
from .rule import Rule

if TYPE_CHECKING:
    from .base import PluginBase

logger = logging.getLogger("qingci-bot.matcher")


@dataclass
class MatcherContext(MessageContext):
    """匹配器上下文 — 增强版 MessageContext"""

    bot: object | None = None  # Bot 实例引用（运行时注入）
    plugin: PluginBase | None = None
    matcher: Matcher | None = None
    command: str = ""
    args: str = ""
    match: re.Match | None = None
    # 子指令名（subcommand 规则写入，如 "admin ban" 中的 "ban"）
    subcommand: str = ""
    # args_schema 类型化解析后的命令参数字典（handler 按名注入）
    parsed_args: dict = field(default_factory=dict)
    # session_state 由主项目 Dispatcher 运行时注入（TTL 会话状态存储）
    session_state: Any | None = field(default=None, repr=False)

    @classmethod
    def from_message_context(
        cls,
        ctx: MessageContext,
        bot: object | None = None,
        plugin: PluginBase | None = None,
        matcher: Matcher | None = None,
    ) -> MatcherContext:
        base_changes = {f.name: getattr(ctx, f.name) for f in fields(MessageContext)}
        return replace(
            cls(**base_changes),
            bot=bot,
            plugin=plugin,
            matcher=matcher,
        )


@dataclass(eq=False)
class Matcher:
    """事件匹配器"""

    handler: Callable
    rule: Rule = field(default_factory=Rule)
    permission: Permission = field(default_factory=lambda: EVERYONE)
    priority: int = 1
    block: bool = True
    temp: bool = False
    disabled: bool = False  # 用户手动禁用：不参与调度，但保留在插件中
    owner: str = ""
    event_type: str = "message"
    meta: dict = field(default_factory=dict)


# ============ 工厂函数 ============


def _create_matcher(
    handler: Callable,
    rule: Rule,
    permission: Permission,
    priority: int,
    block: bool,
    temp: bool,
    event_type: str = "message",
) -> Matcher:
    return Matcher(
        handler=handler,
        rule=rule,
        permission=permission,
        priority=priority,
        block=block,
        temp=temp,
        event_type=event_type,
    )


def on_message(
    rule: Rule | None = None,
    permission: Permission | None = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
    description: str = "",
) -> Callable:
    """注册消息匹配器（装饰器工厂）"""

    def decorator(func: Callable) -> Matcher:
        m = _create_matcher(
            handler=func,
            rule=rule or Rule(),
            permission=permission or EVERYONE,
            priority=priority,
            block=block,
            temp=temp,
            event_type="message",
        )
        m.meta["description"] = description
        _collect_module_matcher(m)
        return m

    return decorator


def on_command(
    cmd: str | tuple[str, ...],
    rule: Rule | None = None,
    permission: Permission | None = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
    description: str = "",
    aliases: tuple[str, ...] = (),
    subcommands: dict | None = None,
    args_schema: dict | None = None,
) -> Callable:
    """注册命令匹配器（支持别名 / 子指令 / 类型化参数）

    用法:
        # 别名：cmd 传 tuple，或显式 aliases
        @on_command("help", aliases=("帮助", "h"))
        async def help_cmd(ctx: MatcherContext) -> str:
            return "可用命令: ..."

        # 子指令：路由到子指令 handler（"admin ban user" -> ban_handler）
        @on_command("admin", subcommands={
            "ban": ban_handler,
            "unban": unban_handler,
        })
        async def admin(ctx: MatcherContext) -> str:
            return "子指令: ban/unban"

        # 类型化参数：args_schema 自动解析命令参数并注入 handler 形参
        @on_command("weather", args_schema={"city": str, "days": int})
        async def weather(ctx: MatcherContext, city: str = "", days: int = 1) -> str:
            return f"{city}: {days} 天预报"
    """
    from .rule import command as _command
    from .rule import subcommand as _subcommand

    cmd_list = (cmd,) if isinstance(cmd, str) else tuple(cmd)
    if aliases:
        cmd_list = tuple(dict.fromkeys((*cmd_list, *aliases)))
    combined_rule = _command(cmd_list)
    if rule:
        combined_rule = combined_rule & rule

    def decorator(func: Callable) -> Matcher:
        parent_rule = combined_rule
        # 父指令排除已声明的子指令，避免父指令拦截子指令消息
        if subcommands:
            for sub_name in subcommands:
                parent_rule = parent_rule & ~_subcommand(cmd_list[0], sub_name)

        parent = _create_matcher(
            handler=func,
            rule=parent_rule,
            permission=permission or EVERYONE,
            priority=priority,
            block=block,
            temp=temp,
            event_type="message",
        )
        # 回填元信息：命令主名（tuple 取第一个）与描述，供 /help 等使用
        parent.meta["command"] = cmd_list[0]
        parent.meta["description"] = description
        if args_schema:
            parent.meta["args_schema"] = dict(args_schema)
        _collect_module_matcher(parent)

        # 子指令：每个子指令独立 Matcher（同一 priority，规则与父指令互斥），
        # 子指令消息必然命中对应子指令 Matcher，父指令不会拦截
        if subcommands:
            for sub_name, sub_handler in subcommands.items():
                sub_rule = combined_rule & _subcommand(cmd_list[0], sub_name)
                sub_m = _create_matcher(
                    handler=sub_handler,
                    rule=sub_rule,
                    permission=permission or EVERYONE,
                    priority=priority,
                    block=block,
                    temp=temp,
                    event_type="message",
                )
                sub_m.meta["command"] = f"{cmd_list[0]} {sub_name}"
                sub_m.meta["description"] = description
                sub_m.meta["is_subcommand"] = True
                if args_schema:
                    sub_m.meta["args_schema"] = dict(args_schema)
                _collect_module_matcher(sub_m)
        return parent

    return decorator


def on_startswith(
    prefix: str | tuple[str, ...],
    rule: Rule | None = None,
    permission: Permission | None = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
    description: str = "",
) -> Callable:
    """注册前缀匹配器"""
    from .rule import startswith as _startswith

    combined_rule = _startswith(prefix)
    if rule:
        combined_rule = combined_rule & rule

    def decorator(func: Callable) -> Matcher:
        m = _create_matcher(
            handler=func,
            rule=combined_rule,
            permission=permission or EVERYONE,
            priority=priority,
            block=block,
            temp=temp,
            event_type="message",
        )
        m.meta["description"] = description
        _collect_module_matcher(m)
        return m

    return decorator


def on_keyword(
    keywords: str | tuple[str, ...],
    rule: Rule | None = None,
    permission: Permission | None = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
    description: str = "",
) -> Callable:
    """注册关键词匹配器"""
    from .rule import keyword as _keyword

    kws = (keywords,) if isinstance(keywords, str) else keywords
    combined_rule = _keyword(*kws)
    if rule:
        combined_rule = combined_rule & rule

    def decorator(func: Callable) -> Matcher:
        m = _create_matcher(
            handler=func,
            rule=combined_rule,
            permission=permission or EVERYONE,
            priority=priority,
            block=block,
            temp=temp,
            event_type="message",
        )
        m.meta["description"] = description
        _collect_module_matcher(m)
        return m

    return decorator


def on_notice(
    rule: Rule | None = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
) -> Callable:
    """注册通知事件匹配器"""

    def decorator(func: Callable) -> Matcher:
        m = _create_matcher(
            handler=func,
            rule=rule or Rule(),
            permission=EVERYONE,
            priority=priority,
            block=block,
            temp=temp,
            event_type="notice",
        )
        _collect_module_matcher(m)
        return m

    return decorator


def on_request(
    rule: Rule | None = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
) -> Callable:
    """注册请求事件匹配器"""

    def decorator(func: Callable) -> Matcher:
        m = _create_matcher(
            handler=func,
            rule=rule or Rule(),
            permission=EVERYONE,
            priority=priority,
            block=block,
            temp=temp,
            event_type="request",
        )
        _collect_module_matcher(m)
        return m

    return decorator


# ============ 模块级 Matcher 收集 ============

# 模块级 Matcher 收集栈：插件加载时设置，收集到的 matcher 关联到当前插件。
# 用线程锁保护全局收集器，防御未来在 begin/end 之间引入 await 时两个并发
# 加载（如 API 触发的 reload）交错污染全局变量。
_matcher_collector: list | None = None
_collector_lock = threading.Lock()


def _collect_module_matcher(matcher: Matcher):
    """收集模块级注册的 Matcher

    两种情况：
    1. PluginManager 加载模块时设置了 _matcher_collector -> 收集到列表
    2. 插件在 on_load 中手动 self.matchers.append() -> 不收集（已是 Matcher 对象）
    """
    with _collector_lock:
        if _matcher_collector is not None:
            _matcher_collector.append(matcher)
    # 否则：matcher 直接作为装饰器返回值，由调用方自行处理


def begin_module_collection() -> list:
    """开始收集模块级 Matcher，返回收集列表"""
    global _matcher_collector
    with _collector_lock:
        _matcher_collector = []
        return _matcher_collector


def end_module_collection():
    """结束收集"""
    global _matcher_collector
    with _collector_lock:
        _matcher_collector = None
