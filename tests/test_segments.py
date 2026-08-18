"""消息段抽象与 v12 事件解析测试（方案 A 迁移 Phase 1）

覆盖：
- MessageSegment 工厂（产出 OneBot 12 标准段）
- Message 容器（纯文本提取 / mention / image / reply）
- v11 <-> v12 段双向转换
- MessageContext.from_v12_event（v12 事件归一化）
- events.py 对 v12 事件 dict 的解析（detail_type 映射）
"""

from qingci_plugin_sdk import (
    FriendRequestEvent,
    GroupIncreaseNotice,
    GroupRequestEvent,
    Message,
    MessageContext,
    MessageSegment,
    normalize_v11_segment,
    parse_notice_event,
    parse_request_event,
    parse_v12_event,
    segments_to_v11,
    segments_to_v12,
)

# ============ MessageSegment 工厂 ============


def test_text_segment():
    seg = MessageSegment.text("你好")
    assert seg == {"type": "text", "data": {"text": "你好"}}


def test_mention_segment_stringifies_id():
    seg = MessageSegment.mention(123456)
    assert seg == {"type": "mention", "data": {"user_id": "123456"}}


def test_mention_all_segment():
    assert MessageSegment.mention_all() == {"type": "mention_all", "data": {}}


def test_media_segments_use_file_id():
    assert MessageSegment.image("img-1") == {"type": "image", "data": {"file_id": "img-1"}}
    assert MessageSegment.voice("v-1") == {"type": "voice", "data": {"file_id": "v-1"}}
    assert MessageSegment.video("vd-1") == {"type": "video", "data": {"file_id": "vd-1"}}
    assert MessageSegment.audio("a-1") == {"type": "audio", "data": {"file_id": "a-1"}}
    assert MessageSegment.file("f-1") == {"type": "file", "data": {"file_id": "f-1"}}


def test_reply_segment():
    seg = MessageSegment.reply("6283")
    assert seg == {"type": "reply", "data": {"message_id": "6283"}}
    seg2 = MessageSegment.reply("6283", user_id="456")
    assert seg2["data"] == {"message_id": "6283", "user_id": "456"}


def test_location_segment():
    seg = MessageSegment.location(31.03, 121.44, title="T", content="C")
    assert seg["type"] == "location"
    assert seg["data"]["latitude"] == 31.03
    assert seg["data"]["title"] == "T"


# ============ Message 容器 ============


def test_message_extract_plain_text():
    msg = Message(
        [
            MessageSegment.text("你好"),
            MessageSegment.mention("10001"),
            MessageSegment.text("世界"),
            MessageSegment.mention_all(),
        ]
    )
    assert msg.extract_plain_text() == "你好@10001世界@所有人"
    assert str(msg) == msg.extract_plain_text()


def test_message_mentions_and_images():
    msg = Message(
        [
            MessageSegment.text("看图"),
            MessageSegment.image("img-1"),
            MessageSegment.mention("10001"),
            MessageSegment.image("img-2"),
        ]
    )
    assert msg.mentions() == ["10001"]
    assert msg.images() == ["img-1", "img-2"]
    assert msg.first_reply() is None


def test_message_first_reply():
    msg = Message([MessageSegment.text("x"), MessageSegment.reply("99")])
    assert msg.first_reply() == {"message_id": "99"}


def test_message_from_v11():
    v11 = [
        {"type": "text", "data": {"text": "hi"}},
        {"type": "at", "data": {"qq": "123"}},
        {"type": "at", "data": {"qq": "all"}},
        {"type": "image", "data": {"file": "f.png", "url": "http://x/f.png"}},
    ]
    msg = Message.from_v11(v11)
    assert msg.segments[0] == {"type": "text", "data": {"text": "hi"}}
    assert msg.segments[1] == {"type": "mention", "data": {"user_id": "123"}}
    assert msg.segments[2] == {"type": "mention_all", "data": {}}
    assert msg.segments[3] == {"type": "image", "data": {"file_id": "f.png"}}
    assert msg.mentions() == ["123"]


def test_message_from_raw_variants():
    assert Message.from_raw("纯文本").as_dicts() == [{"type": "text", "data": {"text": "纯文本"}}]
    assert Message.from_raw([]).as_dicts() == []
    v12 = [{"type": "text", "data": {"text": "a"}}]
    assert Message.from_raw(v12).as_dicts() == v12


# ============ v11 <-> v12 转换 ============


def test_normalize_v11_at():
    assert normalize_v11_segment({"type": "at", "data": {"qq": "123"}}) == {
        "type": "mention",
        "data": {"user_id": "123"},
    }
    for all_val in ("all", "0", ""):
        assert (
            normalize_v11_segment({"type": "at", "data": {"qq": all_val}})["type"] == "mention_all"
        )


def test_normalize_v11_media():
    assert normalize_v11_segment({"type": "record", "data": {"file": "v.amr"}}) == {
        "type": "voice",
        "data": {"file_id": "v.amr"},
    }
    assert normalize_v11_segment({"type": "image", "data": {"url": "http://a/b.png"}})["data"] == {
        "file_id": "http://a/b.png"
    }


def test_normalize_v11_reply_face_forward():
    assert normalize_v11_segment({"type": "reply", "data": {"id": "88"}}) == {
        "type": "reply",
        "data": {"message_id": "88"},
    }
    face = normalize_v11_segment({"type": "face", "data": {"id": "123"}})
    assert face["type"] == "text"
    assert "表情" in face["data"]["text"]
    fwd = normalize_v11_segment({"type": "forward", "data": {"id": "9"}})
    assert fwd["type"] == "text"
    assert "合并转发" in fwd["data"]["text"]


def test_to_v11_roundtrip():
    v12 = [
        {"type": "text", "data": {"text": "hi"}},
        {"type": "mention", "data": {"user_id": "123"}},
        {"type": "mention_all", "data": {}},
        {"type": "voice", "data": {"file_id": "v.amr"}},
        {"type": "image", "data": {"file_id": "f.png"}},
        {"type": "reply", "data": {"message_id": "88"}},
    ]
    v11 = segments_to_v11(v12)
    assert v11 == [
        {"type": "text", "data": {"text": "hi"}},
        {"type": "at", "data": {"qq": "123"}},
        {"type": "at", "data": {"qq": "all"}},
        {"type": "record", "data": {"file": "v.amr"}},
        {"type": "image", "data": {"file": "f.png"}},
        {"type": "reply", "data": {"id": "88"}},
    ]
    # 往返：v11 -> v12 -> v11 保持稳定
    assert segments_to_v11(segments_to_v12(v11)) == v11


# ============ MessageContext.from_v12_event ============


def test_context_from_v12_group_message():
    raw = {
        "id": "evt-1",
        "impl": "go_onebot_qq",
        "platform": "qq",
        "self_id": "123",
        "time": 1632847927.5,
        "type": "message",
        "detail_type": "group",
        "sub_type": "",
        "message_id": "6283",
        "message": [
            {"type": "text", "data": {"text": "你好 "}},
            {"type": "mention", "data": {"user_id": "123"}},
            {"type": "image", "data": {"file_id": "img-1"}},
        ],
        "alt_message": "你好 @123 [图片]",
        "user_id": "456",
        "group_id": "789",
    }
    ctx = MessageContext.from_v12_event(raw)
    assert ctx.type == "message"
    assert ctx.detail_type == "group"
    assert ctx.post_type == "message"  # 兼容派生
    assert ctx.message_type == "group"  # 兼容派生
    assert ctx.platform == "qq"
    assert ctx.self_id == "123"
    assert ctx.user_id == "456"
    assert ctx.group_id == "789"
    assert ctx.message_id == "6283"
    assert ctx.plain_text == "你好 @123"  # text 段 + mention 补全
    assert ctx.raw_message == "你好 @123 [图片]"  # alt_message 优先
    assert ctx.at_list == ["123"]
    assert ctx.is_at_bot is True  # mention 命中 self_id
    assert ctx.images == ["img-1"]
    assert ctx.segments[2] == {"type": "image", "data": {"file_id": "img-1"}}


def test_context_from_v12_private_message():
    raw = {
        "type": "message",
        "detail_type": "private",
        "platform": "telegram",
        "self_id": "bot-1",
        "user_id": "u-2",
        "message_id": "m-3",
        "message": [{"type": "text", "data": {"text": "hi"}}],
        "alt_message": "hi",
    }
    ctx = MessageContext.from_v12_event(raw)
    assert ctx.message_type == "private"
    assert ctx.platform == "telegram"
    assert ctx.raw_message == "hi"


def test_context_from_v12_guild_message():
    raw = {
        "type": "message",
        "detail_type": "guild.message",
        "platform": "qq",
        "self_id": "123",
        "user_id": "456",
        "guild_id": "g-1",
        "channel_id": "c-1",
        "message_id": "m-4",
        "message": [{"type": "text", "data": {"text": "频道消息"}}],
    }
    ctx = MessageContext.from_v12_event(raw)
    assert ctx.message_type == "channel"  # guild.* 归类为 channel
    assert ctx.guild_id == "g-1"
    assert ctx.channel_id == "c-1"


def test_context_v11_segments_compat_view():
    raw = {
        "type": "message",
        "detail_type": "group",
        "self_id": "1",
        "user_id": "2",
        "message": [
            {"type": "mention", "data": {"user_id": "2"}},
            {"type": "voice", "data": {"file_id": "v.amr"}},
        ],
    }
    ctx = MessageContext.from_v12_event(raw)
    v11 = ctx.as_v11_segments()
    assert v11 == [
        {"type": "at", "data": {"qq": "2"}},
        {"type": "record", "data": {"file": "v.amr"}},
    ]
    assert ctx.as_v12_segments() == ctx.segments
    assert ctx.message.mentions() == ["2"]


# ============ events.py v12 解析 ============


def test_parse_notice_v12_group_member_increase():
    raw = {
        "id": "e1",
        "impl": "go_onebot_qq",
        "platform": "qq",
        "type": "notice",
        "detail_type": "group_member_increase",
        "sub_type": "approve",
        "self_id": "1",
        "user_id": "100",
        "group_id": "200",
        "time": 1786889000,
    }
    ev = parse_notice_event(raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert ev.notice_type == "group_increase"  # detail_type 映射回 v11 命名
    assert ev.detail_type == "group_member_increase"
    assert ev.user_id == 100
    assert ev.group_id == 200
    assert ev.sub_type == "approve"
    assert ev.platform == "qq"
    assert ev.event_id == "e1"


def test_parse_notice_v12_ban_subtype():
    ev = parse_notice_event({"type": "notice", "detail_type": "group_member_unban", "user_id": "1"})
    assert ev.notice_type == "group_ban"
    assert ev.sub_type == "lift_ban"


def test_parse_notice_v11_still_works():
    raw = {
        "post_type": "notice",
        "notice_type": "group_increase",
        "user_id": 100,
        "group_id": 200,
    }
    ev = parse_notice_event(raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert ev.notice_type == "group_increase"
    assert ev.user_id == 100


def test_parse_request_v12():
    raw = {
        "type": "request",
        "detail_type": "group",
        "sub_type": "invite",
        "user_id": "100",
        "group_id": "200",
        "comment": "邀请",
        "flag": "flag-1",
    }
    ev = parse_request_event(raw)
    assert isinstance(ev, GroupRequestEvent)
    assert ev.request_type == "group"
    assert ev.group_id == 200
    assert ev.flag == "flag-1"

    ev2 = parse_request_event(
        {"type": "request", "detail_type": "friend", "user_id": "100", "comment": "hi"}
    )
    assert isinstance(ev2, FriendRequestEvent)
    assert ev2.request_type == "friend"


def test_parse_v12_event_router():
    raw = {
        "type": "notice",
        "detail_type": "group_member_increase",
        "user_id": "1",
        "group_id": "2",
    }
    ev = parse_v12_event(raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert parse_v12_event({"type": "meta", "detail_type": "heartbeat"}) is None
    assert parse_v12_event({"type": "message", "user_id": "1"}) is None


def test_notice_type_mapping_helpers():
    from qingci_plugin_sdk import detail_type_to_notice_type, notice_type_to_detail_type

    assert detail_type_to_notice_type("group_member_increase") == "group_increase"
    assert notice_type_to_detail_type("group_increase") == "group_member_increase"
    assert detail_type_to_notice_type("unknown_x") == "unknown_x"
