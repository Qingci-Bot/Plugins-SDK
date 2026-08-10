"""插件基类 — 插件 SDK 独立版本"""

from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

from .context import MessageContext

if TYPE_CHECKING:
    from .matcher import Matcher


class PluginBase(ABC):
    """插件基类

    支持两种消息处理方式：
    1. 旧式：重写 on_message(ctx) -> Optional[str]
    2. 新式：在 on_load 中注册 Matcher（self.matchers.append(on_command(...)(handler))）
    """

    # 插件元信息
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    require: list[str] = []

    # 依赖引用（由框架注入）
    bot: Optional[object] = None
    db: Optional[object] = None
    config: Optional[object] = None
    connection: Optional[object] = None
    llm: Optional[object] = None
    scheduler: Optional[Any] = None
    tool_registry: Optional[Any] = None
    knowledge_store: Optional[Any] = None

    # Matcher 列表
    matchers: Optional[list["Matcher"]] = None

    @abstractmethod
    async def on_load(self):
        """插件加载时调用"""
        ...

    @abstractmethod
    async def on_unload(self):
        """插件卸载时调用"""
        ...

    async def on_message(self, ctx: MessageContext) -> Optional[str]:
        """处理消息事件，返回回复文本或 None"""
        return None

    async def on_notice(self, event: dict) -> None:
        """处理通知事件"""
        pass

    async def on_request(self, event: dict) -> Optional[bool]:
        """处理请求事件（加群/加好友），返回 True 同意 / False 拒绝 / None 忽略"""
        return None