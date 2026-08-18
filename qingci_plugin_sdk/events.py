"""类型化事件模型 — notice/request 事件（插件 SDK 独立版本）

OneBot 11 的 notice/request 事件为扁平 dict，字段无类型信息、无补全。
本模块提供类型化 dataclass 模型与解析工厂：

    from qingci_plugin_sdk.events import parse_notice_event

    evt = parse_notice_event(raw_event)          # 自动按 notice_type 返回子类
    evt.notice_type == "group_increase"
    evt.group_id                                 # int，已做安全转换

OneBot 12 迁移（方案 A）：解析入口同时接受 v11 与 v12 两种事件 dict。

- v11：post_type="notice" + notice_type="group_increase"
- v12：type="notice" + detail_type="group_member_increase"

v12 的 detail_type 命名与 v11 的 notice_type 不同（如
group_member_increase 对应 group_increase），解析时自动映射到 v11
命名空间，插件侧事件类（GroupIncreaseNotice 等）保持不变；
v12 基础字段（type / detail_type / event_id / impl / platform）也
被保留在事件对象上供需要时读取。

handler 参数注入：在 Matcher handler 中声明类型化事件参数，
框架按注解自动注入（见主项目 Dispatcher）：

    from qingci_plugin_sdk.events import GroupIncreaseNotice

    @on_notice()
    async def handler(ctx: MatcherContext, event: GroupIncreaseNotice):
        return f"欢迎新成员 {event.user_id}"

零依赖：使用 dataclass 而非 pydantic，插件开发者无需安装额外依赖；
字段按 OneBot 11 规范类型化，非法值安全回退默认（不抛异常）。
"""

from __future__ import annotations

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
    "parse_event",
    "parse_v12_event",
    "detail_type_to_notice_type",
    "notice_type_to_detail_type",
]


def _int(value, default: int = 0) -> int:
    """安全转 int：非法值回退默认，不抛异常"""
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _str(value, default: str = "") -> str:
    """安全转 str：None/缺失回退默认"""
    if value is None:
        return default
    return str(value)


# ============ v11 notice_type <-> v12 detail_type 映射 ============

# v12 detail_type -> v11 notice_type（标准通知事件）
_V12_TO_V11_NOTICE: dict[str, str] = {
    "private_message_delete": "friend_recall",
    "friend_increase": "friend_add",
    "friend_decrease": "friend_recall",  # v11 无直接对应，归入 friend_recall 命名空间
    "group_member_increase": "group_increase",
    "group_member_decrease": "group_decrease",
    "group_message_delete": "group_recall",
    "group_admin_set": "group_admin",
    "group_admin_unset": "group_admin",
    "group_member_ban": "group_ban",
    "group_member_unban": "group_ban",
    "group_file_upload": "group_upload",
    "group_poke": "poke",
    "friend_poke": "poke",
}

# v11 notice_type -> v12 detail_type（反向映射，供事件转发/测试使用）
_V11_TO_V12_NOTICE: dict[str, str] = {
    "friend_recall": "private_message_delete",
    "friend_add": "friend_increase",
    "group_increase": "group_member_increase",
    "group_decrease": "group_member_decrease",
    "group_recall": "group_message_delete",
    "group_admin": "group_admin_set",
    "group_ban": "group_member_ban",
    "group_upload": "group_file_upload",
    "poke": "group_poke",
}


def detail_type_to_notice_type(detail_type: str) -> str:
    """v12 detail_type -> v11 notice_type（未知类型原样返回）"""
    return _V12_TO_V11_NOTICE.get(detail_type, detail_type)


def notice_type_to_detail_type(notice_type: str) -> str:
    """v11 notice_type -> v12 detail_type（未知类型原样返回）"""
    return _V11_TO_V12_NOTICE.get(notice_type, notice_type)


# ============ Notice 事件 ============


@dataclass
class NoticeEvent:
    """通知事件基类（通用字段 + 原始事件）

    字段兼容 v11 命名（notice_type 等）；v12 基础字段（type /
    detail_type / event_id / impl / platform）同时保留。
    """

    time: int = 0  # 事件发生时间戳（秒）
    self_id: int = 0  # 机器人自身 ID
    post_type: str = ""  # 事件类型（恒为 "notice"）
    notice_type: str = ""  # 通知子类型（v11 命名）
    sub_type: str = ""  # 子类型（如 approve/invite/leave/kick）
    user_id: int = 0  # 操作相关用户
    group_id: int = 0  # 群号（群相关事件）
    raw_event: dict = field(default_factory=dict, repr=False)  # 原始事件
    # v12 基础字段
    type: str = ""  # v12 事件类型（恒为 "notice"）
    detail_type: str = ""  # v12 详细类型（如 group_member_increase）
    event_id: str = ""  # v12 事件唯一标识
    impl: str = ""  # OneBot 实现名称
    platform: str = ""  # 平台名称


@dataclass
class GroupIncreaseNotice(NoticeEvent):
    """群成员增加（sub_type: approve/invite/manage）"""

    operator_id: int = 0  # 操作者


@dataclass
class GroupDecreaseNotice(NoticeEvent):
    """群成员减少（sub_type: leave/kick/kick_me）"""

    operator_id: int = 0  # 操作者


@dataclass
class GroupBanNotice(NoticeEvent):
    """群禁言（sub_type: ban/lift_ban）"""

    operator_id: int = 0  # 操作者
    duration: int = 0  # 禁言时长（秒）


@dataclass
class GroupAdminNotice(NoticeEvent):
    """群管理员变动（sub_type: set/unset）"""


@dataclass
class GroupRecallNotice(NoticeEvent):
    """群消息撤回（sub_type: recall）"""

    operator_id: int = 0  # 操作者
    message_id: int = 0  # 被撤回消息 ID


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


@dataclass
class MessageEditedEvent(NoticeEvent):
    """消息编辑（Telegram 扩展事件，notice_type=message_edited）

    由 Telegram `edited_message` 归一化而来（OneBot 事件模型无等价事件，
    以扩展 notice 承载）。编辑不触发消息回复，插件用 on_notice() 消费后
    可读取编辑后的新文本（alt_message）与 v12 段数组（message）。
    """

    message_id: str = ""  # 被编辑消息 ID（OneBot 12 字符串语义）
    alt_message: str = ""  # 编辑后的新文本
    message: list = field(default_factory=list)  # 编辑后的 v12 段数组
    is_at_bot: bool = False  # 编辑内容是否提及了 Bot


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
    "message_edited": (MessageEditedEvent, ("message_id", "alt_message", "message", "is_at_bot")),
}


def parse_notice_event(raw: dict) -> NoticeEvent:
    """按 notice_type 解析通知事件为类型化对象

    同时接受 v11（post_type + notice_type）与 v12（type +
    detail_type）两种事件 dict；v12 的 detail_type 自动映射到 v11
    notice_type 命名空间。

    未知类型回退 NoticeEvent 基类（通用字段仍类型化）；
    字段缺失/非法安全回退默认值，不抛异常。
    """
    # v12 输入：type="notice" + detail_type；映射到 v11 notice_type
    detail_type = _str(raw.get("detail_type"))
    if detail_type:
        notice_type = detail_type_to_notice_type(detail_type)
    else:
        notice_type = _str(raw.get("notice_type"))

    sub_type = _str(raw.get("sub_type"))
    # v12 的 group_admin_unset / group_member_unban 通过 sub_type 区分
    if detail_type == "group_admin_unset":
        sub_type = sub_type or "unset"
    elif detail_type == "group_admin_set":
        sub_type = sub_type or "set"
    elif detail_type == "group_member_unban":
        sub_type = sub_type or "lift_ban"
    elif detail_type == "group_member_ban":
        sub_type = sub_type or "ban"

    kwargs: dict[str, object] = {
        "time": _int(raw.get("time")),
        "self_id": _int(raw.get("self_id")),
        "post_type": _str(raw.get("post_type", "notice")),
        "notice_type": notice_type,
        "sub_type": sub_type,
        "user_id": _int(raw.get("user_id")),
        "group_id": _int(raw.get("group_id")),
        "raw_event": dict(raw),
        "type": _str(raw.get("type", "notice")),
        "detail_type": detail_type or _str(raw.get("detail_type")),
        "event_id": _str(raw.get("id")),
        "impl": _str(raw.get("impl")),
        "platform": _str(raw.get("platform")),
    }
    cls = _NOTICE_CLASSES.get(notice_type, (NoticeEvent, ()))[0]
    for name in _NOTICE_CLASSES.get(notice_type, (NoticeEvent, ()))[1]:
        value = raw.get(name)
        if name == "file":
            kwargs[name] = dict(value) if isinstance(value, dict) else {}
        elif isinstance(value, (dict, list)):
            kwargs[name] = value
        elif isinstance(value, str):
            kwargs[name] = _str(value)  # str 字段（如 message_id/alt_message）原样保留
        elif isinstance(value, bool):
            kwargs[name] = bool(value)  # bool 字段（如 is_at_bot）原样保留
        else:
            kwargs[name] = _int(value)
    return cls(**kwargs)  # type: ignore[arg-type]  # kwargs 值已按字段类型化


# ============ Request 事件 ============


@dataclass
class RequestEvent:
    """请求事件基类（通用字段 + 原始事件）

    字段兼容 v11 命名（request_type 等）；v12 基础字段同时保留。
    """

    time: int = 0  # 事件发生时间戳（秒）
    self_id: int = 0  # 机器人自身 ID
    post_type: str = ""  # 事件类型（恒为 "request"）
    request_type: str = ""  # 请求子类型（friend/group）
    sub_type: str = ""  # 子类型（group: add/invite）
    user_id: int = 0  # 请求者
    comment: str = ""  # 验证信息
    flag: str = ""  # 请求 flag（审批时回传）
    raw_event: dict = field(default_factory=dict, repr=False)  # 原始事件
    # v12 基础字段
    type: str = ""  # v12 事件类型（恒为 "request"）
    detail_type: str = ""  # v12 详细类型（friend / group）
    event_id: str = ""
    impl: str = ""
    platform: str = ""


@dataclass
class FriendRequestEvent(RequestEvent):
    """加好友请求"""


@dataclass
class GroupRequestEvent(RequestEvent):
    """加群请求/邀请（sub_type: add/invite）"""

    group_id: int = 0  # 目标群号


def parse_request_event(raw: dict) -> RequestEvent:
    """按 request_type 解析请求事件为类型化对象

    同时接受 v11（post_type + request_type）与 v12（type +
    detail_type）两种事件 dict。

    未知类型回退 RequestEvent 基类；字段缺失/非法安全回退默认值。
    """
    detail_type = _str(raw.get("detail_type"))
    request_type = detail_type or _str(raw.get("request_type"))
    kwargs: dict[str, object] = {
        "time": _int(raw.get("time")),
        "self_id": _int(raw.get("self_id")),
        "post_type": _str(raw.get("post_type", "request")),
        "request_type": request_type,
        "sub_type": _str(raw.get("sub_type")),
        "user_id": _int(raw.get("user_id")),
        "comment": _str(raw.get("comment")),
        "flag": _str(raw.get("flag")),
        "raw_event": dict(raw),
        "type": _str(raw.get("type", "request")),
        "detail_type": detail_type,
        "event_id": _str(raw.get("id")),
        "impl": _str(raw.get("impl")),
        "platform": _str(raw.get("platform")),
    }
    if request_type == "group":
        kwargs["group_id"] = _int(raw.get("group_id"))
        return GroupRequestEvent(**kwargs)  # type: ignore[arg-type]
    return FriendRequestEvent(**kwargs)  # type: ignore[arg-type]


def parse_event(post_type: str, raw: dict) -> NoticeEvent | RequestEvent | None:
    """通用解析入口：按 post_type 分发到 notice/request 解析

    兼容 v11 调用方式（post_type="notice"/"request"）；若 raw 是
    v12 事件 dict（含 type 字段），自动按其 type 分发。

    非 notice/request 事件返回 None。
    """
    # v12 智能识别：raw 自带 type 且与传入 post_type 不一致时以 raw 为准
    raw_type = _str(raw.get("type"))
    if raw_type and not raw.get("post_type"):
        post_type = raw_type
    if post_type == "notice":
        return parse_notice_event(raw)
    if post_type == "request":
        return parse_request_event(raw)
    return None


def parse_v12_event(raw: dict) -> NoticeEvent | RequestEvent | None:
    """OneBot 12 事件解析入口：按 raw["type"] 分发

    供主项目 Dispatcher 的 v12 归一化链路使用。
    """
    return parse_event(_str(raw.get("type")), raw)
