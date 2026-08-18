"""消息段抽象 — OneBot 12 标准消息段模型（插件 SDK 独立版本）

OneBot 12 的消息段统一为 {type, data} 对象数组，媒体参数统一使用
file_id 引用。本模块提供：

- SegmentType 常量：标准段类型（text/mention/mention_all/image/voice/
  audio/video/file/reply/location）
- MessageSegment 工厂：以静态方法构建标准段 dict，插件无需手写段结构
- Message 容器：段数组的组装、纯文本提取、v11 兼容视图
- normalize_v11_segment / to_v11_segment：与 OneBot 11 段格式互转

设计约束（与 SDK 整体一致）：
- 零第三方依赖，仅使用 dataclass / typing
- 段 dict 即 OneBot 12 规范原样，可被序列化为 JSON 直接作为动作参数

    from qingci_plugin_sdk.segments import Message, MessageSegment

    msg = Message([MessageSegment.text("你好"), MessageSegment.image("file-123")])
    msg.as_dicts()          # [{"type":"text","data":{"text":"你好"}}, ...]
    msg.extract_plain_text()  # "你好"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "SegmentType",
    "MessageSegment",
    "Message",
    "normalize_v11_segment",
    "to_v11_segment",
    "segments_to_v12",
    "segments_to_v11",
]


# ============ 段类型常量 ============


class SegmentType:
    """OneBot 12 标准消息段类型常量"""

    TEXT = "text"
    MENTION = "mention"
    MENTION_ALL = "mention_all"
    IMAGE = "image"
    VOICE = "voice"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    REPLY = "reply"
    LOCATION = "location"


# ============ MessageSegment 工厂 ============


class MessageSegment:
    """消息段工厂 — 产出 OneBot 12 标准 {type, data} 段 dict

    全部为静态方法，返回原生 dict，避免引入额外对象包装，
    便于直接序列化为动作请求参数。
    """

    @staticmethod
    def text(text: str) -> dict[str, Any]:
        """纯文本段"""
        return {"type": SegmentType.TEXT, "data": {"text": str(text)}}

    @staticmethod
    def mention(user_id: str | int) -> dict[str, Any]:
        """提及（@）某用户，user_id 字符串化（OneBot 12 规范）"""
        return {"type": SegmentType.MENTION, "data": {"user_id": str(user_id)}}

    @staticmethod
    def mention_all() -> dict[str, Any]:
        """提及所有人（@全体）"""
        return {"type": SegmentType.MENTION_ALL, "data": {}}

    @staticmethod
    def image(file_id: str) -> dict[str, Any]:
        """图片段（媒体以 file_id 引用）"""
        return {"type": SegmentType.IMAGE, "data": {"file_id": str(file_id)}}

    @staticmethod
    def voice(file_id: str) -> dict[str, Any]:
        """语音段（现场录制的声音）"""
        return {"type": SegmentType.VOICE, "data": {"file_id": str(file_id)}}

    @staticmethod
    def audio(file_id: str) -> dict[str, Any]:
        """音频段（音乐/音频文件）"""
        return {"type": SegmentType.AUDIO, "data": {"file_id": str(file_id)}}

    @staticmethod
    def video(file_id: str) -> dict[str, Any]:
        """视频段"""
        return {"type": SegmentType.VIDEO, "data": {"file_id": str(file_id)}}

    @staticmethod
    def file(file_id: str) -> dict[str, Any]:
        """文件段"""
        return {"type": SegmentType.FILE, "data": {"file_id": str(file_id)}}

    @staticmethod
    def reply(message_id: str | int, user_id: str | int = "") -> dict[str, Any]:
        """回复段（message_id 必填；user_id 为被回复消息发送者，发送时可省）"""
        data: dict[str, Any] = {"message_id": str(message_id)}
        if user_id not in ("", 0, None):
            data["user_id"] = str(user_id)
        return {"type": SegmentType.REPLY, "data": data}

    @staticmethod
    def location(
        latitude: float,
        longitude: float,
        title: str = "",
        content: str = "",
    ) -> dict[str, Any]:
        """位置段"""
        return {
            "type": SegmentType.LOCATION,
            "data": {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "title": str(title),
                "content": str(content),
            },
        }


# ============ Message 容器 ============


@dataclass
class Message:
    """消息容器 — 一组 OneBot 12 消息段

    提供段数组的便捷组装与视图转换；段本身保持 {type, data} 原生 dict，
    可无包装地作为 send_message 动作的 message 参数。
    """

    segments: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.segments = [dict(s) for s in self.segments]

    def __bool__(self) -> bool:
        return bool(self.segments)

    def __len__(self) -> int:
        return len(self.segments)

    def __iter__(self):
        return iter(self.segments)

    def __str__(self) -> str:
        """可读文本表示（alt_message 语义）"""
        return self.extract_plain_text()

    # ---------- 组装 ----------

    def append(self, segment: dict[str, Any]) -> Message:
        self.segments.append(dict(segment))
        return self

    def extend(self, segments: list[dict[str, Any]]) -> Message:
        self.segments.extend(dict(s) for s in segments)
        return self

    # ---------- 视图转换 ----------

    def as_dicts(self) -> list[dict[str, Any]]:
        """原生 v12 段数组（可直接作为动作参数）"""
        return [dict(s) for s in self.segments]

    def as_v11(self) -> list[dict[str, Any]]:
        """转换为 OneBot 11 段数组（兼容旧插件/旧平台读取）"""
        return segments_to_v11(self.segments)

    # ---------- 提取 ----------

    def extract_plain_text(self) -> str:
        """拼接全部 text 段为纯文本（mention/mention_all 也补全为 @ 文本）

        mention 以 "@user_id" 形式补全、mention_all 以 "@所有人" 补全，
        保证读出来的文本尽量接近用户可见内容。
        """
        parts: list[str] = []
        for seg in self.segments:
            seg_type = seg.get("type", "")
            data = seg.get("data", {}) if isinstance(seg.get("data"), dict) else {}
            if seg_type == SegmentType.TEXT:
                parts.append(str(data.get("text", "")))
            elif seg_type == SegmentType.MENTION:
                parts.append(f"@{data.get('user_id', '')}")
            elif seg_type == SegmentType.MENTION_ALL:
                parts.append("@所有人")
        return "".join(parts)

    def mentions(self) -> list[str]:
        """所有 mention 段的 user_id（字符串列表）"""
        return [
            str(seg["data"]["user_id"])
            for seg in self.segments
            if seg.get("type") == SegmentType.MENTION
            and isinstance(seg.get("data"), dict)
            and seg["data"].get("user_id") is not None
        ]

    def images(self) -> list[str]:
        """所有 image 段的 file_id 或 url（优先 file_id）"""
        result: list[str] = []
        for seg in self.segments:
            if seg.get("type") != SegmentType.IMAGE or not isinstance(seg.get("data"), dict):
                continue
            data = seg["data"]
            result.append(str(data.get("file_id") or data.get("url") or ""))
        return result

    def first_reply(self) -> dict[str, Any] | None:
        """第一条 reply 段的 data（无回复段返回 None）"""
        for seg in self.segments:
            if seg.get("type") == SegmentType.REPLY and isinstance(seg.get("data"), dict):
                return dict(seg["data"])
        return None

    @classmethod
    def from_v11(cls, segments: list[dict[str, Any]]) -> Message:
        """从 OneBot 11 段数组构造（自动归一化为 v12 段）"""
        return cls(segments_to_v12(segments))

    @classmethod
    def from_raw(cls, message: Any) -> Message:
        """从任意入参构造：段数组 / v11 段数组 / 纯文本字符串

        供 CE 入口归一化层使用，屏蔽平台消息格式差异。
        """
        if isinstance(message, Message):
            return cls(message.as_dicts())
        if isinstance(message, str):
            return cls([MessageSegment.text(message)])
        if isinstance(message, (list, tuple)):
            segments = list(message)
            if segments and all(isinstance(s, dict) for s in segments):
                if any(cls._looks_v11(s) for s in segments):
                    return cls(segments_to_v12(segments))
                return cls(segments)
        return cls()

    @staticmethod
    def _looks_v11(seg: dict[str, Any]) -> bool:
        """判断单段是否为 v11 格式（供 from_raw 嗅探）

        - at / at_all / record / face / forward 为 v11 专属段类型
        - reply 在 v11/v12 均存在：v11 用 id，v12 用 message_id，依字段判别
        """
        seg_type = seg.get("type")
        if seg_type in ("at", "at_all", "record", "face", "forward"):
            return True
        if seg_type == "reply":
            data = seg.get("data", {})
            return bool(isinstance(data, dict) and "id" in data and "message_id" not in data)
        return False


# ============ v11 <-> v12 转换 ============

# v11 媒体段类型 -> v12 段类型（record 在 v12 中语义为 voice）
_V11_MEDIA_MAP: dict[str, str] = {
    "image": SegmentType.IMAGE,
    "record": SegmentType.VOICE,
    "video": SegmentType.VIDEO,
    "audio": SegmentType.AUDIO,
    "file": SegmentType.FILE,
}


def _v11_at_all(value: Any) -> bool:
    """判断 v11 at 段是否为 @全体"""
    return str(value).lower() in ("all", "0", "")


def normalize_v11_segment(seg: dict[str, Any]) -> dict[str, Any]:
    """将一条 OneBot 11 段归一化为 OneBot 12 段

    映射规则：
    - at (qq=all/0)      -> mention_all
    - at (qq=数字)        -> mention (user_id 字符串化)
    - image/record/video -> image/voice/video（file/url -> file_id 优先）
    - reply (id)         -> reply (message_id)
    - face/forward       -> 保留为 text 降级（OneBot 12 无标准段，避免丢信息）
    - 其余（text 等）     -> 原样返回
    """
    seg_type = seg.get("type", "")
    data = seg.get("data", {})
    if not isinstance(data, dict):
        data = {}

    if seg_type == "at":
        qq = data.get("qq")
        if _v11_at_all(qq):
            return {"type": SegmentType.MENTION_ALL, "data": {}}
        return {"type": SegmentType.MENTION, "data": {"user_id": str(qq)}}

    if seg_type in _V11_MEDIA_MAP:
        # v11 用 file/url 表达媒体，v12 用 file_id；优先 file 再 url。
        # record 在 v12 中拆分为 voice（现场语音）；type 随之映射。
        file_id = data.get("file") or data.get("url") or ""
        return {"type": _V11_MEDIA_MAP[seg_type], "data": {"file_id": str(file_id)}}

    if seg_type == "reply":
        new_data: dict[str, Any] = {"message_id": str(data.get("id", ""))}
        return {"type": SegmentType.REPLY, "data": new_data}

    if seg_type == "face":
        return MessageSegment.text(f"[表情 {data.get('id', '')}]")

    if seg_type == "forward":
        return MessageSegment.text(f"[合并转发 {data.get('id', '')}]")

    return {"type": seg_type, "data": dict(data)}


def to_v11_segment(seg: dict[str, Any]) -> dict[str, Any]:
    """将一条 OneBot 12 段转换为 OneBot 11 段（兼容视图）

    反向映射：
    - mention            -> at (qq=user_id)
    - mention_all        -> at (qq=all)
    - voice              -> record（v11 语音段）
    - image/video/audio/file -> 原段（file_id 放入 file 字段）
    - reply              -> reply (id=message_id)
    - location/text 等    -> 原样返回
    """
    seg_type = seg.get("type", "")
    data = seg.get("data", {})
    if not isinstance(data, dict):
        data = {}

    if seg_type == SegmentType.MENTION:
        return {"type": "at", "data": {"qq": str(data.get("user_id", ""))}}

    if seg_type == SegmentType.MENTION_ALL:
        return {"type": "at", "data": {"qq": "all"}}

    if seg_type == SegmentType.VOICE:
        return {"type": "record", "data": {"file": str(data.get("file_id", ""))}}

    if seg_type in (SegmentType.IMAGE, SegmentType.AUDIO, SegmentType.VIDEO, SegmentType.FILE):
        return {"type": seg_type, "data": {"file": str(data.get("file_id", ""))}}

    if seg_type == SegmentType.REPLY:
        return {"type": "reply", "data": {"id": str(data.get("message_id", ""))}}

    return {"type": seg_type, "data": dict(data)}


def segments_to_v12(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量：v11 段数组 -> v12 段数组"""
    return [normalize_v11_segment(s) for s in segments]


def segments_to_v11(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量：v12 段数组 -> v11 段数组（兼容视图）"""
    return [to_v11_segment(s) for s in segments]
