"""类型化事件模型 — notice/request 事件（插件 SDK 独立版本）

OneBot 11 的 notice/request 事件为扁平 dict，字段无类型信息、无补全。
本模块提供类型化 dataclass 模型与解析工厂：

    from qingci_plugin_sdk.events import parse_notice_event

    evt = parse_notice_event(raw_event)          # 自动按 notice_type 返回子类
    evt.notice_type == "group_increase"
    evt.group_id                                 # int，已做安全转换

handler 参数注入：在 Matcher handler 中声明类型化事件参数，
框架按注解自动注入（见主项目 Dispatcher）：

    from qingci_plugin_sdk.events import GroupIncreaseNotice

    @on_notice()
    async def handler(ctx: MatcherContext, event: GroupIncreaseNotice):
        return f"欢迎新成员 {event.user_id}"

零依赖：使用 dataclass 而非 pydantic，插件开发者无需安装额外依赖；
字段按 OneBot 11 规范类型化，非法值安全回退默认（不抛异常）。
"""

from dataclasses import dataclass, field

__all__ = [
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
    "RequestEvent",
    "FriendRequestEvent",
    "GroupRequestEvent",
    "parse_notice_event",
    "parse_request_event",
]


def _int(value, default: int = 0) -> int:
    """安全转 int：非法值回退默认，不抛异常"""
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


# ============ Notice 事件 ============


@dataclass
class NoticeEvent:
    """通知事件基类（通用字段 + 原始事件）"""

    time: int = 0          # 事件发生时间戳（秒）
    self_id: int = 0       # 机器人自身 QQ 号
    post_type: str = ""    # 事件类型（恒为 "notice"）
    notice_type: str = ""  # 通知子类型
    sub_type: str = ""     # 子类型（如 approve/invite/leave/kick）
    user_id: int = 0       # 操作相关用户
    group_id: int = 0      # 群号（群相关事件）
    raw_event: dict = field(default_factory=dict, repr=False)  # 原始事件


@dataclass
class GroupIncreaseNotice(NoticeEvent):
    """群成员增加（sub_type: approve/invite/manage）"""

    operator_id: int = 0  # 操作者 QQ


@dataclass
class GroupDecreaseNotice(NoticeEvent):
    """群成员减少（sub_type: leave/kick/kick_me）"""

    operator_id: int = 0  # 操作者 QQ


@dataclass
class GroupBanNotice(NoticeEvent):
    """群禁言（sub_type: ban/lift_ban）"""

    operator_id: int = 0   # 操作者 QQ
    duration: int = 0      # 禁言时长（秒）


@dataclass
class GroupAdminNotice(NoticeEvent):
    """群管理员变动（sub_type: set/unset）"""


@dataclass
class GroupRecallNotice(NoticeEvent):
    """群消息撤回（sub_type: recall）"""

    operator_id: int = 0   # 操作者 QQ
    message_id: int = 0    # 被撤回消息 ID


@dataclass
class FriendRecallNotice(NoticeEvent):
    """好友消息撤回"""

    message_id: int = 0  # 被撤回消息 ID


@dataclass
class FriendAddNotice(NoticeEvent):
    """好友添加（sub_type: add）"""


@dataclass
class GroupUploadNotice(NoticeEvent):
    """群文件上传"""

    file: dict = field(default_factory=dict)  # {"id":..,"name":..,"size":..,"busid":..}


@dataclass
class PokeNotice(NoticeEvent):
    """戳一戳（sub_type: poke）"""

    target_id: int = 0  # 被戳用户


_NOTICE_CLASSES: dict[str, tuple[type[NoticeEvent], tuple[str, ...]]] = {
    "group_increase": (GroupIncreaseNotice, ("operator_id",)),
    "group_decrease": (GroupDecreaseNotice, ("operator_id",)),
    "group_ban": (GroupBanNotice, ("operator_id", "duration")),
    "group_admin": (GroupAdminNotice, ()),
    "group_recall": (GroupRecallNotice, ("operator_id", "message_id")),
    "friend_recall": (FriendRecallNotice, ("message_id",)),
    "friend_add": (FriendAddNotice, ()),
    "group_upload": (GroupUploadNotice, ("file",)),
    "poke": (PokeNotice, ("target_id",)),
}


def parse_notice_event(raw: dict) -> NoticeEvent:
    """按 notice_type 解析通知事件为类型化对象

    未知类型回退 NoticeEvent 基类（通用字段仍类型化）；
    字段缺失/非法安全回退默认值，不抛异常。
    """
    kwargs: dict[str, object] = {
        "time": _int(raw.get("time")),
        "self_id": _int(raw.get("self_id")),
        "post_type": str(raw.get("post_type", "notice")),
        "notice_type": str(raw.get("notice_type", "")),
        "sub_type": str(raw.get("sub_type", "")),
        "user_id": _int(raw.get("user_id")),
        "group_id": _int(raw.get("group_id")),
        "raw_event": dict(raw),
    }
    notice_type = str(kwargs["notice_type"])
    cls = _NOTICE_CLASSES.get(notice_type, (NoticeEvent, ()))[0]
    for name in _NOTICE_CLASSES.get(notice_type, (NoticeEvent, ()))[1]:
        value = raw.get(name)
        if name == "file":
            kwargs[name] = dict(value) if isinstance(value, dict) else {}
        elif isinstance(value, (dict, list)):
            kwargs[name] = value
        else:
            kwargs[name] = _int(value)
    return cls(**kwargs)  # type: ignore[arg-type]  # kwargs 值已按字段类型化


# ============ Request 事件 ============


@dataclass
class RequestEvent:
    """请求事件基类（通用字段 + 原始事件）"""

    time: int = 0          # 事件发生时间戳（秒）
    self_id: int = 0       # 机器人自身 QQ 号
    post_type: str = ""    # 事件类型（恒为 "request"）
    request_type: str = ""  # 请求子类型（friend/group）
    sub_type: str = ""     # 子类型（group: add/invite）
    user_id: int = 0       # 请求者 QQ
    comment: str = ""      # 验证信息
    flag: str = ""         # 请求 flag（审批时回传）
    raw_event: dict = field(default_factory=dict, repr=False)  # 原始事件


@dataclass
class FriendRequestEvent(RequestEvent):
    """加好友请求"""


@dataclass
class GroupRequestEvent(RequestEvent):
    """加群请求/邀请（sub_type: add/invite）"""

    group_id: int = 0  # 目标群号


def parse_request_event(raw: dict) -> RequestEvent:
    """按 request_type 解析请求事件为类型化对象

    未知类型回退 RequestEvent 基类；字段缺失/非法安全回退默认值。
    """
    kwargs: dict[str, object] = {
        "time": _int(raw.get("time")),
        "self_id": _int(raw.get("self_id")),
        "post_type": str(raw.get("post_type", "request")),
        "request_type": str(raw.get("request_type", "")),
        "sub_type": str(raw.get("sub_type", "")),
        "user_id": _int(raw.get("user_id")),
        "comment": str(raw.get("comment", "")),
        "flag": str(raw.get("flag", "")),
        "raw_event": dict(raw),
    }
    if kwargs["request_type"] == "group":
        kwargs["group_id"] = _int(raw.get("group_id"))
        return GroupRequestEvent(**kwargs)  # type: ignore[arg-type]
    return FriendRequestEvent(**kwargs)  # type: ignore[arg-type]


def parse_event(post_type: str, raw: dict) -> NoticeEvent | RequestEvent | None:
    """通用解析入口：按 post_type 分发到 notice/request 解析

    非 notice/request 事件返回 None。
    """
    if post_type == "notice":
        return parse_notice_event(raw)
    if post_type == "request":
        return parse_request_event(raw)
    return None
