"""消息上下文 — 插件 SDK 独立定义

与主项目 bot.core.dispatcher.MessageContext 保持一致，
插件开发无需依赖主项目即可使用。
"""

from dataclasses import dataclass, field


@dataclass
class MessageContext:
    """解析后的消息上下文"""

    # 原始事件
    raw_event: dict = field(default_factory=dict)

    # 基础信息
    post_type: str = ""
    message_type: str = ""  # group / private
    sub_type: str = ""  # normal / anonymous / notice
    message_id: str = ""
    user_id: int = 0
    group_id: int = 0
    self_id: int = 0  # Bot 自己的 QQ 号
    platform: str = "onebot"  # 消息来源平台（onebot / telegram / ...）

    # 消息内容
    raw_message: str = ""  # CQ 码原始文本
    plain_text: str = ""  # 纯文本
    at_list: list[int] = field(default_factory=list)
    is_at_bot: bool = False
    images: list[str] = field(default_factory=list)

    # 发送者信息
    sender: dict = field(default_factory=dict)

    # 完整消息段
    segments: list[dict] = field(default_factory=list)

    @property
    def sender_name(self) -> str:
        """发送者昵称"""
        return str(self.sender.get("nickname", "") or self.sender.get("card", ""))
