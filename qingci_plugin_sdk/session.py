"""会话阶梯 — 多轮交互控制流（插件 SDK 独立版本）

借鉴 NoneBot2 的会话阶梯（send/pause/finish/reject）设计，为插件提供
声明式的多轮对话能力：handler 不再"一次事件一次回复"，而是可以
挂起等待用户下一条消息，逐轮收集信息后再结束。

使用方式（在 Matcher handler 中）：
    async def wizard(ctx: MatcherContext):
        await ctx.session.send("开始向导")          # 发送但不结束
        await ctx.session.pause("请输入你的名字")    # 发送并等待下一条消息
        # 下一条消息到达后，同一 handler 被再次调用（context 续接）
        name = ctx.plain_text
        await ctx.session.finish(f"你好，{name}！")   # 发送并结束阶梯

控制流语义：
    - send(text):   发送文本，handler 继续执行（不抛异常）
    - pause(text):  发送文本（可选）并抛出 PauseException，
                    框架挂起等待同会话的下一条消息
    - finish(text): 发送文本（可选）并抛出 FinishException，
                    结束本会话阶梯
    - reject(text): 发送文本（可选）并抛出 RejectException，
                    拒绝当前输入、保留阶梯继续等待

实现约定：Session 是协议层对象，发送行为由宿主（主项目 Dispatcher）
在构造时注入 send_fn；控制流异常由宿主捕获并驱动状态机。
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

__all__ = ["Session", "PauseException", "FinishException", "RejectException"]


class PauseException(Exception):
    """会话暂停：等待同会话的下一条消息

    由 session.pause() 抛出。宿主捕获后挂起阶梯，下一条消息续接同一 handler。
    """

    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(message or "会话暂停")


class FinishException(Exception):
    """会话结束：终止阶梯并清理等待状态

    由 session.finish() 抛出。宿主捕获后结束阶梯，不再续接。
    """

    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(message or "会话结束")


class RejectException(Exception):
    """会话拒绝：拒绝当前输入，保留阶梯继续等待

    由 session.reject() 抛出。宿主捕获后保持阶梯挂起，等待下一条消息。
    """

    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(message or "会话拒绝")


class Session:
    """会话阶梯对象 — 多轮交互控制句柄

    handler 通过 ctx.session 获取。发送行为由宿主注入的 send_fn 提供；
    插件在独立工作区（无宿主）使用时，send_fn 可为 None，此时
    send/pause/finish/reject 仅执行控制流（不发送文本），便于冒烟测试。
    """

    def __init__(
        self,
        send_fn: Callable[[str], Awaitable[None]] | None = None,
        *,
        step_key: str = "",
        step_ttl: float = 300.0,
    ):
        self._send_fn = send_fn
        self.step_key = step_key  # 会话阶梯键（宿主注入，用于定位等待中的阶梯）
        self.step_ttl = step_ttl  # 阶梯挂起超时（秒）

    async def send(self, text: str) -> None:
        """发送文本消息，不结束会话（handler 可继续执行）"""
        if self._send_fn is not None:
            await self._send_fn(text)

    def _rebind_send(self, send_fn: Callable[[str], Awaitable[None]]) -> None:
        """重绑发送函数（宿主在多轮续接时调用，复用同一实例的新会话）

        跨轮复用 Session 实例时，上一条消息的 ctx 可能已失效，
        需要将发送通道重绑到当前消息的回复上下文。
        """
        self._send_fn = send_fn

    async def pause(self, text: str | None = None) -> None:
        """发送文本（可选）并挂起，等待同会话的下一条消息"""
        if text and self._send_fn is not None:
            await self._send_fn(text)
        raise PauseException(text)

    async def finish(self, text: str | None = None) -> None:
        """发送文本（可选）并结束本会话阶梯"""
        if text and self._send_fn is not None:
            await self._send_fn(text)
        raise FinishException(text)

    async def reject(self, text: str | None = None) -> None:
        """发送文本（可选），拒绝当前输入并继续等待"""
        if text and self._send_fn is not None:
            await self._send_fn(text)
        raise RejectException(text)
