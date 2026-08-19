"""Qingci-Bot 插件 SDK — 独立可安装的插件开发工具包

使用方式:
    from qingci_plugin_sdk import PluginBase, on_command, MatcherContext

安装:
    uv pip install -e .    # 从 Plugins-SDK 目录
"""

__version__ = "1.9.1"

from .base import PluginBase, PluginStatus
from .context import MessageContext
from .events import (
    FriendAddNotice,
    FriendRecallNotice,
    FriendRequestEvent,
    GroupAdminNotice,
    GroupBanNotice,
    GroupDecreaseNotice,
    GroupIncreaseNotice,
    GroupRecallNotice,
    GroupRequestEvent,
    GroupUploadNotice,
    MessageEditedEvent,
    NoticeEvent,
    PokeNotice,
    RequestEvent,
    detail_type_to_notice_type,
    notice_type_to_detail_type,
    parse_event,
    parse_notice_event,
    parse_request_event,
    parse_v12_event,
)
from .i18n import I18n
from .llm_tool import LlmToolSpec, llm_tool
from .matcher import (
    Matcher,
    MatcherContext,
    begin_module_collection,
    end_module_collection,
    on_command,
    on_keyword,
    on_message,
    on_notice,
    on_request,
    on_startswith,
)
from .permission import (
    ADMIN,
    EVERYONE,
    GROUP,
    GROUP_MEMBER,
    MEMBER,
    PRIVATE,
    SUPERUSER,
    USER,
    Permission,
    describe_permission,
)
from .ratelimit import RateLimiter
from .rule import (
    Rule,
    command,
    contains,
    endswith,
    fullmatch,
    is_group,
    is_private,
    keyword,
    rate_limit,
    regex,
    startswith,
    subcommand,
    to_me,
)
from .segments import (
    Message,
    MessageSegment,
    SegmentType,
    normalize_v11_segment,
    segments_to_v11,
    segments_to_v12,
    to_v11_segment,
)
from .session import FinishException, PauseException, RejectException, Session

__all__ = [
    # 版本
    "__version__",
    # 基础
    "PluginBase",
    "PluginStatus",
    "MessageContext",
    # i18n
    "I18n",
    # 类型化事件
    "NoticeEvent",
    "GroupIncreaseNotice",
    "GroupDecreaseNotice",
    "GroupBanNotice",
    "GroupAdminNotice",
    "GroupRecallNotice",
    "FriendRecallNotice",
    "FriendAddNotice",
    "GroupUploadNotice",
    "PokeNotice",
    "MessageEditedEvent",
    "RequestEvent",
    "FriendRequestEvent",
    "GroupRequestEvent",
    "parse_event",
    "parse_notice_event",
    "parse_request_event",
    "parse_v12_event",
    "detail_type_to_notice_type",
    "notice_type_to_detail_type",
    # 消息段
    "SegmentType",
    "MessageSegment",
    "Message",
    "normalize_v11_segment",
    "to_v11_segment",
    "segments_to_v11",
    "segments_to_v12",
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
    # 会话阶梯
    "Session",
    "PauseException",
    "FinishException",
    "RejectException",
]
