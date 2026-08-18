"""消息上下文 — 插件 SDK 独立定义

与主项目 bot.core.dispatcher.MessageContext 保持一致，
插件开发无需依赖主项目即可使用。

OneBot 12 迁移（方案 A）后的字段约定：
- 主数据源为 v12 事件（type / detail_type / message[]），由 from_v12_event
  构造或由主项目 Dispatcher 归一化后填充
- post_type / message_type / sub_type / raw_message 保留为兼容字段：
  post_type 与 message_type 由 v12 字段派生，供存量插件继续读取
- segments 统一存放 OneBot 12 标准段数组（{type, data}，媒体用 file_id）；
  as_v11_segments() 提供 v11 兼容视图（at -> at、voice -> record 等）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .segments import Message, segments_to_v11

__all__ = ["MessageContext"]


@dataclass
class MessageContext:
    """解析后的消息上下文"""

    # 原始事件
    raw_event: dict = field(default_factory=dict)

    # 基础信息（v12 字段优先）
    type: str = ""  # v12 事件类型（message / notice / request / meta）
    detail_type: str = ""  # v12 事件详细类型（private / group / ...）
    event_id: str = ""  # v12 事件唯一标识
    channel_id: str = ""  # 频道 ID（guild 场景，v12 两级群组）
    guild_id: str = ""  # 群组 ID（guild 场景）

    # 基础信息（v11 兼容字段，由 v12 字段派生或由旧适配器填充）
    post_type: str = ""  # 事件类型（message / notice / request / meta）
    message_type: str = ""  # group / private（由 detail_type 派生）
    sub_type: str = ""  # normal / anonymous / notice
    message_id: str = ""
    user_id: str | int = ""  # v11 为数字，v12 为字符串
    group_id: str | int = ""  # 同上
    self_id: str | int = ""  # 机器人自身 ID（v11 数字 / v12 字符串）
    platform: str = "onebot"  # 消息来源平台（onebot / telegram / ...）

    # 消息内容
    raw_message: str = ""  # 可读原始文本（v12 下为 alt_message 语义）
    plain_text: str = ""  # 纯文本
    at_list: list = field(default_factory=list)  # mention 用户 ID 列表（字符串）
    is_at_bot: bool = False
    images: list[str] = field(default_factory=list)

    # 发送者信息
    sender: dict = field(default_factory=dict)

    # 完整消息段（OneBot 12 标准段数组）
    segments: list[dict] = field(default_factory=list)

    # ---------- 兼容视图 ----------

    @property
    def sender_name(self) -> str:
        """发送者昵称"""
        return str(self.sender.get("nickname", "") or self.sender.get("card", "") or "")

    def as_v11_segments(self) -> list[dict]:
        """v11 兼容段视图（at -> at、voice -> record、mention_all -> at all 等）"""
        return segments_to_v11(self.segments)

    def as_v12_segments(self) -> list[dict]:
        """原生 v12 段数组（可直接作为 send_message 动作参数）"""
        return [dict(s) for s in self.segments]

    @property
    def message(self) -> Message:
        """以 Message 容器读取段数组（提取纯文本/mention/image 等）"""
        return Message(self.segments)

    @classmethod
    def from_v12_event(cls, raw: dict) -> MessageContext:
        """从 OneBot 12 事件 dict 构造上下文（v12 归一化入口）

        v12 事件示例：
            {
              "id": "...", "impl": "...", "platform": "qq",
              "self_id": "123", "time": 1632847927.5,
              "type": "message", "detail_type": "group", "sub_type": "",
              "message_id": "6283",
              "message": [{"type": "text", "data": {"text": "hi"}}],
              "alt_message": "hi", "user_id": "123456"
            }
        """
        ctx = cls(
            raw_event=dict(raw),
            type=str(raw.get("type", "")),
            detail_type=str(raw.get("detail_type", "")),
            event_id=str(raw.get("id", "")),
            platform=str(raw.get("platform", "") or "onebot"),
            self_id=str(raw.get("self_id", "") or ""),
            message_id=str(raw.get("message_id", "") or ""),
            user_id=str(raw.get("user_id", "") or ""),
            group_id=str(raw.get("group_id", "") or ""),
            sender=dict(raw.get("sender", {}) or {}),
        )
        # post_type 派生（meta 保持 meta；其余照抄 type）
        ctx.post_type = str(raw.get("type", ""))
        # message_type 由 detail_type 派生：private/group 直接映射，
        # guild.* 归类为 channel 并回填 guild/channel id
        detail_type = ctx.detail_type
        if detail_type.startswith("guild."):
            ctx.message_type = "channel"
            ctx.guild_id = str(raw.get("guild_id", "") or "")
            ctx.channel_id = str(raw.get("channel_id", "") or "")
        elif detail_type in ("private", "group"):
            ctx.message_type = detail_type
        # 消息段归一化（自动处理 v11 段输入）
        msg = Message.from_raw(raw.get("message"))
        ctx.segments = msg.as_dicts()
        # 便捷字段计算
        ctx.raw_message = str(raw.get("alt_message", "") or msg.extract_plain_text())
        ctx.plain_text = msg.extract_plain_text()
        ctx.at_list = msg.mentions()
        ctx.images = msg.images()
        if ctx.at_list:
            ctx.is_at_bot = ctx.self_id in ctx.at_list
        # 补充时间字段到 raw_event（v12 用 float，秒）
        return ctx
