"""Qingci-Bot 插件 SDK — 独立可安装的插件开发工具包

使用方式:
    from qingci_plugin_sdk import PluginBase, on_command, MatcherContext

安装:
    pip install -e .    # 从 Plugins-Dev 目录
"""

from .base import PluginBase
from .context import MessageContext
from .matcher import (
    Matcher,
    MatcherContext,
    on_message,
    on_command,
    on_startswith,
    on_keyword,
    on_notice,
    on_request,
    begin_module_collection,
    end_module_collection,
)
from .permission import (
    Permission,
    EVERYONE,
    SUPERUSER,
    ADMIN,
    PRIVATE,
    GROUP,
    MEMBER,
    USER,
    GROUP_MEMBER,
)
from .ratelimit import RateLimiter
from .rule import (
    Rule,
    startswith,
    endswith,
    fullmatch,
    contains,
    regex,
    command,
    to_me,
    is_private,
    is_group,
    keyword,
    rate_limit,
)

__all__ = [
    # 基础
    "PluginBase",
    "MessageContext",
    # Matcher
    "Matcher",
    "MatcherContext",
    "on_message",
    "on_command",
    "on_startswith",
    "on_keyword",
    "on_notice",
    "on_request",
    "begin_module_collection",
    "end_module_collection",
    # Permission
    "Permission",
    "EVERYONE",
    "SUPERUSER",
    "ADMIN",
    "PRIVATE",
    "GROUP",
    "MEMBER",
    "USER",
    "GROUP_MEMBER",
    # Rule
    "Rule",
    "startswith",
    "endswith",
    "fullmatch",
    "contains",
    "regex",
    "command",
    "to_me",
    "is_private",
    "is_group",
    "keyword",
    "rate_limit",
    # RateLimit
    "RateLimiter",
]