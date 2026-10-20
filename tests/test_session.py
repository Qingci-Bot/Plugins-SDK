"""会话阶梯测试 — Session 控制流与异常语义"""

from __future__ import annotations

import pytest

from qingci_plugin_sdk.session import (
    FinishException,
    PauseException,
    RejectException,
    Session,
)


class _Recorder:
    def __init__(self):
        self.messages: list[str] = []

    async def send(self, text: str) -> None:
        self.messages.append(text)


def test_send_does_not_interrupt():
    rec = _Recorder()
    session = Session(rec.send)

    async def run():
        await session.send("第一句")
        await session.send("第二句")
        return "继续执行了"

    import asyncio

    assert asyncio.run(run()) == "继续执行了"
    assert rec.messages == ["第一句", "第二句"]


def test_send_without_send_fn_is_noop():
    session = Session()

    async def run():
        await session.send("无宿主时静默")

    import asyncio

    asyncio.run(run())


@pytest.mark.asyncio
async def test_pause_sends_and_raises():
    rec = _Recorder()
    session = Session(rec.send)
    with pytest.raises(PauseException) as exc:
        await session.pause("请提供名字")
    assert exc.value.message == "请提供名字"
    assert rec.messages == ["请提供名字"]


@pytest.mark.asyncio
async def test_finish_sends_and_raises():
    rec = _Recorder()
    session = Session(rec.send)
    with pytest.raises(FinishException) as exc:
        await session.finish("完成")
    assert exc.value.message == "完成"
    assert rec.messages == ["完成"]


@pytest.mark.asyncio
async def test_reject_keeps_waiting():
    rec = _Recorder()
    session = Session(rec.send)
    with pytest.raises(RejectException):
        await session.reject("输入无效")
    assert rec.messages == ["输入无效"]


@pytest.mark.asyncio
async def test_exceptions_default_message():
    session = Session()
    with pytest.raises(PauseException) as e1:
        await session.pause()
    assert "暂停" in str(e1.value)
    with pytest.raises(FinishException) as e2:
        await session.finish()
    assert "结束" in str(e2.value)
    with pytest.raises(RejectException) as e3:
        await session.reject()
    assert "拒绝" in str(e3.value)


def test_rebind_send_switches_channel():
    rec1 = _Recorder()
    rec2 = _Recorder()
    session = Session(rec1.send)
    session._rebind_send(rec2.send)

    import asyncio

    async def run():
        await session.send("重绑")

    asyncio.run(run())
    assert rec1.messages == []
    assert rec2.messages == ["重绑"]


def test_step_metadata():
    session = Session(step_key="onebot:private:1", step_ttl=60.0)
    assert session.step_key == "onebot:private:1"
    assert session.step_ttl == 60.0


def test_dynamic_attributes_round_trip():
    """跨轮状态：插件可在 Session 上挂任意属性（py.typed 下也须可通过类型检查）"""
    session = Session()
    session.step = "ask_age"
    session.name = "小明"

    assert session.step == "ask_age"
    assert session.name == "小明"


def test_unset_dynamic_attribute_raises_attribute_error():
    """未设置的动态属性照常抛 AttributeError（getattr 默认值语义不变）"""
    session = Session()

    with pytest.raises(AttributeError):
        _ = session.not_set
    assert getattr(session, "not_set", "fallback") == "fallback"
