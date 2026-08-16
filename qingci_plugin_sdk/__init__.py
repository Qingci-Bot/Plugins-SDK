"""Qingci-Bot 插件 SDK — 独立可安装的插件开发工具包

使用方式:
    from qingci_plugin_sdk import PluginBase, on_command, MatcherContext

安装:
    uv pip install -e .    # 从 Plugins-SDK 目录
"""

from .base import PluginBase, PluginStatus
from .context import MessageContext
from .i18n import I18n
from .llm_tool import LlmToolSpec, llm_tool
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
    describe_permission,
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
    subcommand,
    to_me,
    is_private,
    is_group,
    keyword,
    rate_limit,
)

__all__ = [
    # 基础
    "PluginBase",
    "PluginStatus",
    "MessageContext",
    # i18n
    "I18n",
    # LLM 工具
    "LlmToolSpec",
    "llm_tool",
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
    "describe_permission",
    # Rule
    "Rule",
    "startswith",
    "endswith",
    "fullmatch",
    "contains",
    "regex",
    "command",
    "subcommand",
    "to_me",
    "is_private",
    "is_group",
    "keyword",
    "rate_limit",
    # RateLimit
    "RateLimiter",
]