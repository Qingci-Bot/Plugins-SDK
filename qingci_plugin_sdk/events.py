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
from typing import Any

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
    "FriendPokeNotice",
    "GroupLuckyKingNotice",
    "GroupHonorChangeNotice",
    "GroupCardNotice",
    "GroupEssenceNotice",
    "GroupSignInNotice",
    "RequestEvent",
    "FriendRequestEvent",
    "GroupRequestEvent",
    "parse_notice_event",
    "parse_request_event",
    "parse_event",
    "parse_v12_event",
    "translate_v11_event",
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
    # friend_decrease（好友减少）在 v11 无对应通知类型：
    # 不映射，避免归入 friend_recall（消息撤回）命名空间导致监听
    # 撤回事件的插件收到错误的"好友删除"语义通知
    "group_member_increase": "group_increase",
    "group_member_decrease": "group_decrease",
    "group_message_delete": "group_recall",
    "group_admin_set": "group_admin",
    "group_admin_unset": "group_admin",
    "group_member_ban": "group_ban",
    "group_member_unban": "group_ban",
    "group_file_upload": "group_upload",
    "group_poke": "poke",
    "friend_poke": "friend_poke",
    # 扩展通知（NapCat / LLBot 等实现）：v12 无标准对应，保持同名
    "group_lucky_king": "group_lucky_king",
    "group_honor_change": "group_honor_change",
    "group_card": "group_card",
    "group_essence": "essence",
    "group_sign_in": "group_sign_in",
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
    # 扩展通知（v11 常见于 NapCat / LLBot 等扩展协议端）
    "friend_poke": "friend_poke",
    "group_lucky_king": "group_lucky_king",
    "group_honor_change": "group_honor_change",
    "group_card": "group_card",
    "essence": "group_essence",
    "group_sign_in": "group_sign_in",
}


def detail_type_to_notice_type(detail_type: str) -> str:
    """v12 detail_type -> v11 notice_type（未知类型原样返回）"""
    return _V12_TO_V11_NOTICE.get(detail_type, detail_type)


def notice_type_to_detail_type(notice_type: str, sub_type: str = "") -> str:
    """v11 notice_type -> v12 detail_type（未知类型原样返回）

    按 sub_type 细分的类型（group_admin / group_ban）在 sub_type 缺失时
    给出保守默认（group_admin -> group_admin_unset、group_ban ->
    group_member_ban），与 OneBot 12 语义一致。
    """
    if notice_type == "group_admin":
        return "group_admin_set" if sub_type == "set" else "group_admin_unset"
    if notice_type == "group_ban":
        return "group_member_unban" if sub_type == "lift_ban" else "group_member_ban"
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
class FriendPokeNotice(NoticeEvent):
    """好友戳一戳（扩展通知，NapCat / LLBot 等）"""

    target_id: int = 0  # 被戳用户


@dataclass
class GroupLuckyKingNotice(NoticeEvent):
    """群红包运气王（扩展通知）"""

    target_id: int = 0  # 运气王用户


@dataclass
class GroupHonorChangeNotice(NoticeEvent):
    """群成员荣誉变更（扩展通知）"""

    honor_type: str = ""  # 荣誉类型（talkative/performer/emotion 等）


@dataclass
class GroupCardNotice(NoticeEvent):
    """群名片变更（扩展通知）"""

    card_new: str = ""  # 新名片
    card_old: str = ""  # 旧名片


@dataclass
class GroupEssenceNotice(NoticeEvent):
    """群精华消息（扩展通知，sub_type: add/delete）"""

    message_id: int = 0  # 精华消息 ID
    operation: str = ""  # 操作（add/delete）


@dataclass
class GroupSignInNotice(NoticeEvent):
    """群签到（扩展通知，部分协议端实现）"""


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
    "friend_poke": (FriendPokeNotice, ("target_id",)),
    "group_lucky_king": (GroupLuckyKingNotice, ("target_id",)),
    "group_honor_change": (GroupHonorChangeNotice, ("honor_type",)),
    "group_card": (GroupCardNotice, ("card_new", "card_old")),
    "essence": (GroupEssenceNotice, ("message_id", "operation")),
    "group_sign_in": (GroupSignInNotice, ()),
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


# ============ v11 -> v12 事件翻译（协议映射单一来源） ============

# notice 翻译时已由 _base_fields 规范化/显式设置的键，其余原始键一律保留
_NOTICE_STRUCT_KEYS = frozenset(
    {
        "type",
        "detail_type",
        "sub_type",
        "id",
        "impl",
        "platform",
        "self_id",
        "time",
        "post_type",
        "notice_type",
        "user_id",
        "group_id",
        "operator_id",
    }
)


def translate_v11_event(event: dict, *, impl: str = "") -> dict[str, Any]:
    """OneBot 11 事件 dict -> OneBot 12 事件 dict（平台无关）

    供适配器/宿主把 v11 事件归一化为 v12 事件模型（type / detail_type /
    message[]），使核心只消费 v12 事件：
    - message: post_type -> type；message_type -> detail_type；
      raw_message -> alt_message；含 CQ 码的字符串消息解析为 v12 段数组
    - notice:  notice_type -> detail_type（group_admin / group_ban 按
      sub_type 细分）
    - request: request_type -> detail_type
    - meta:    meta_event_type -> detail_type

    无法识别的事件类型原样返回（防御性，不丢事件）。platform 保留事件
    原值（默认空），impl 由调用方传入（如 "onebot11"）；宿主可在返回后
    补充平台字段。
    """
    from .segments import parse_cq_string

    post_type = event.get("post_type", "")

    def _base_fields(event_type: str, detail_type: str) -> dict[str, Any]:
        return {
            "type": event_type,
            "detail_type": detail_type,
            "sub_type": str(event.get("sub_type", "")),
            "id": str(event.get("message_id") or event.get("flag") or ""),
            "impl": impl,
            "platform": str(event.get("platform", "") or ""),
            "self_id": str(event.get("self_id", "") or ""),
            "time": event.get("time", 0),
        }

    if post_type == "message":
        v12 = _base_fields("message", str(event.get("message_type", "")))
        # v11 message 可能是字符串（含 CQ 码）或段数组：
        # 字符串含 CQ 码时解析为 v12 段数组（否则 @bot 的 CQ:at 会被
        # 整体包成 text 段，导致 is_at_bot / at_list 失真）
        raw_message = event.get("message", [])
        if isinstance(raw_message, str) and "CQ:" in raw_message:
            raw_message = parse_cq_string(raw_message)
        v12.update(
            {
                "message_id": str(event.get("message_id", "") or ""),
                "message": raw_message,
                "alt_message": str(event.get("raw_message", "") or ""),
                "user_id": str(event.get("user_id", "") or ""),
                "group_id": str(event.get("group_id", "") or ""),
                "sender": event.get("sender", {}) or {},
            }
        )
        return v12

    if post_type == "notice":
        notice_type = str(event.get("notice_type", ""))
        detail_type = notice_type_to_detail_type(notice_type, str(event.get("sub_type", "")))
        v12 = _base_fields("notice", detail_type)
        v12.update(
            {
                "user_id": str(event.get("user_id", "") or ""),
                "group_id": str(event.get("group_id", "") or ""),
                "operator_id": str(event.get("operator_id", "") or ""),
            }
        )
        # 携带 v11 原始通知字段，供 LLM 事件缓冲等读取；
        # 拷贝除已规范化结构键外的全部原始键（保留 honor_type /
        # card_new / card_old / operation / duration / target_id /
        # file / message_id 等扩展字段），避免 OB11 独缺扩展通知字段。
        v12.update({key: value for key, value in event.items() if key not in _NOTICE_STRUCT_KEYS})
        return v12

    if post_type == "request":
        v12 = _base_fields("request", str(event.get("request_type", "")))
        v12.update(
            {
                "user_id": str(event.get("user_id", "") or ""),
                "group_id": str(event.get("group_id", "") or ""),
                "comment": str(event.get("comment", "") or ""),
                "flag": str(event.get("flag", "") or ""),
            }
        )
        return v12

    if post_type == "meta_event":
        v12 = _base_fields("meta", str(event.get("meta_event_type", "")))
        v12["sub_type"] = str(event.get("sub_type", ""))
        if "status" in event:
            v12["status"] = event["status"]
        return v12

    return dict(event)
