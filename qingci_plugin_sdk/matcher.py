"""匹配器系统 — 插件 SDK 独立版本

核心概念：
- Matcher: 绑定 handler + rule + permission + priority 的匹配单元
- MatcherContext: 增强版 MessageContext，注入 bot/plugin/matcher 引用
- 工厂函数: on_message / on_command / on_startswith / on_keyword / on_notice / on_request
"""

import logging
import re
from dataclasses import dataclass, field, fields, replace
from typing import Callable, Optional, TYPE_CHECKING, Union

from .context import MessageContext
from .permission import EVERYONE, Permission
from .rule import Rule

if TYPE_CHECKING:
    from .base import PluginBase

logger = logging.getLogger("qingci-bot.matcher")


@dataclass
class MatcherContext(MessageContext):
    """匹配器上下文 — 增强版 MessageContext"""

    bot: Optional[object] = None       # Bot 实例引用（运行时注入）
    plugin: Optional["PluginBase"] = None
    matcher: Optional["Matcher"] = None
    command: str = ""
    args: str = ""
    match: Optional[re.Match] = None

    @classmethod
    def from_message_context(
        cls,
        ctx: MessageContext,
        bot: Optional[object] = None,
        plugin: Optional["PluginBase"] = None,
        matcher: Optional["Matcher"] = None,
    ) -> "MatcherContext":
        base_changes = {f.name: getattr(ctx, f.name) for f in fields(MessageContext)}
        return replace(
            cls(**base_changes),
            bot=bot,
            plugin=plugin,
            matcher=matcher,
        )


@dataclass
class Matcher:
    """事件匹配器"""

    handler: Callable
    rule: Rule = field(default_factory=Rule)
    permission: Permission = field(default_factory=lambda: EVERYONE)
    priority: int = 1
    block: bool = True
    temp: bool = False
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
    rule: Rule = None,
    permission: Permission = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
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
        _collect_module_matcher(m)
        return m
    return decorator


def on_command(
    cmd: Union[str, tuple[str, ...]],
    rule: Rule = None,
    permission: Permission = None,
    priority: int = 1,
    block: bool = True,
    temp: bool = False,
    description: str = "",
) -> Callable:
    """注册命令匹配器"""
    from .rule import command as _command
    combined_rule = _command(cmd)
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
        m.meta["command"] = cmd[0] if isinstance(cmd, tuple) else cmd
        m.meta["description"] = description
        _collect_module_matcher(m)
        return m
    return decorator


def on_startswith(
    prefix: Union[str, tuple[str, ...]],
    rule: Rule = None,
    permission: Permission = None,
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
    keywords: Union[str, tuple[str, ...]],
    rule: Rule = None,
    permission: Permission = None,
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
    rule: Rule = None,
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
    rule: Rule = None,
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

_matcher_collector: Optional[list] = None


def _collect_module_matcher(matcher: Matcher):
    if _matcher_collector is not None:
        _matcher_collector.append(matcher)


def begin_module_collection() -> list:
    global _matcher_collector
    _matcher_collector = []
    return _matcher_collector


def end_module_collection():
    global _matcher_collector
    _matcher_collector = None