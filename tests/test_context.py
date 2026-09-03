"""MessageContext 测试 — from_v12_event 归一化与兼容视图"""

from __future__ import annotations

from qingci_plugin_sdk.context import MessageContext


def _v12_message(segments: list[dict], **extra) -> dict:
    event = {
        "id": "evt-1",
        "impl": "napcat",
        "platform": "qq",
        "self_id": "60001",
        "time": 1632847927.5,
        "type": "message",
        "detail_type": "group",
        "sub_type": "normal",
        "message_id": "6283",
        "message": segments,
        "alt_message": "",
        "user_id": "10001",
        "group_id": "20001",
        "sender": {"nickname": "小明"},
    }
    event.update(extra)
    return event


def test_from_v12_message_type_and_plain_text():
    ctx = MessageContext.from_v12_event(_v12_message([{"type": "text", "data": {"text": "你好"}}]))
    assert ctx.message_type == "group"
    assert ctx.post_type == "message"
    assert ctx.plain_text == "你好"
    assert ctx.raw_message == "你好"
    assert ctx.platform == "qq"
    assert ctx.user_id == "10001"
    assert ctx.group_id == "20001"


def test_from_v12_private():
    ev = _v12_message([{"type": "text", "data": {"text": "hi"}}], detail_type="private")
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.message_type == "private"


def test_from_v12_guild_maps_to_channel():
    ev = _v12_message(
        [{"type": "text", "data": {"text": "hi"}}],
        detail_type="guild.message",
        guild_id="30001",
        channel_id="30002",
    )
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.message_type == "channel"
    assert ctx.guild_id == "30001"
    assert ctx.channel_id == "30002"


def test_from_v12_at_bot_detection():
    ev = _v12_message(
        [
            {"type": "text", "data": {"text": "你好"}},
            {"type": "mention", "data": {"user_id": "60001"}},
        ]
    )
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.is_at_bot is True
    assert ctx.at_list == ["60001"]


def test_from_v12_images_extracted():
    ev = _v12_message([{"type": "image", "data": {"file_id": "file-abc"}}])
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.images == ["file-abc"]


def test_from_v12_string_message_parsed():
    # 含 CQ 码的字符串走 Message.from_raw 解析为段数组
    ev = _v12_message("[CQ:at,qq=60001] 你好")
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.plain_text == "@60001 你好"
    assert ctx.at_list == ["60001"]
    assert ctx.is_at_bot is True


def test_self_id_fallback_to_self_object():
    ev = _v12_message([{"type": "text", "data": {"text": "hi"}}])
    ev.pop("self_id")
    ev["self"] = {"user_id": "60001"}
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.self_id == "60001"


def test_sender_name_prefers_nickname():
    ctx = MessageContext.from_v12_event(_v12_message([], sender={"nickname": "小红"}))
    assert ctx.sender_name == "小红"
    ctx2 = MessageContext.from_v12_event(_v12_message([], sender={"nickname": "", "card": "名片"}))
    assert ctx2.sender_name == "名片"


def test_as_v11_segments_convert_mention():
    ev = _v12_message([{"type": "mention", "data": {"user_id": "10001"}}])
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.as_v11_segments() == [{"type": "at", "data": {"qq": "10001"}}]


def test_as_v12_segments_copies_dicts():
    ev = _v12_message([{"type": "text", "data": {"text": "x"}}])
    ctx = MessageContext.from_v12_event(ev)
    segs = ctx.as_v12_segments()
    assert segs == [{"type": "text", "data": {"text": "x"}}]
    # 返回的是新列表（顶层拷贝），追加/修改不污染内部段数组
    segs.append({"type": "text", "data": {"text": "追加"}})
    segs[0]["type"] = "改"
    assert len(ctx.segments) == 1
    assert ctx.segments[0]["type"] == "text"


def test_message_property():
    ev = _v12_message(
        [{"type": "text", "data": {"text": "hi"}}, {"type": "image", "data": {"file_id": "f"}}]
    )
    ctx = MessageContext.from_v12_event(ev)
    assert ctx.message.extract_plain_text() == "hi"
    assert ctx.message.images() == ["f"]


def test_empty_event_defaults():
    ctx = MessageContext.from_v12_event({})
    assert ctx.plain_text == ""
    assert ctx.message_type == ""
    assert ctx.segments == []
