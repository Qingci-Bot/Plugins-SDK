"""v11 -> v12 事件翻译（translate_v11_event）测试

覆盖：message（含 CQ 码解析）/ notice（group_admin、group_ban 按
sub_type 细分）/ request / meta / 未知事件透传，以及映射对称性
（v11 notice_type -> v12 detail_type -> v11 notice_type 往返一致）。
"""

from qingci_plugin_sdk.events import (
    detail_type_to_notice_type,
    notice_type_to_detail_type,
    translate_v11_event,
)

# ============ message ============


def test_translate_message():
    v12 = translate_v11_event(
        {
            "post_type": "message",
            "message_type": "group",
            "message_id": 6283,
            "user_id": 10001,
            "group_id": 20001,
            "self_id": 20002,
            "raw_message": "你好",
            "message": [{"type": "text", "data": {"text": "你好"}}],
        },
        impl="onebot11",
    )
    assert v12["type"] == "message"
    assert v12["detail_type"] == "group"
    assert v12["message_id"] == "6283"
    assert v12["user_id"] == "10001"
    assert v12["group_id"] == "20001"
    assert v12["self_id"] == "20002"
    assert v12["alt_message"] == "你好"
    assert v12["impl"] == "onebot11"


def test_translate_message_cq_string():
    """含 CQ 码的字符串消息解析为 v12 段数组（@bot 识别不丢）"""
    v12 = translate_v11_event(
        {
            "post_type": "message",
            "message_type": "group",
            "message_id": "1",
            "message": "[CQ:at,qq=20002] /ping",
            "raw_message": "[CQ:at,qq=20002] /ping",
            "self_id": "20002",
        }
    )
    assert v12["message"] == [
        {"type": "mention", "data": {"user_id": "20002"}},
        {"type": "text", "data": {"text": " /ping"}},
    ]


def test_translate_message_without_cq_keeps_raw():
    """不含 CQ 的字符串消息保持原值（与段数组路径一致）"""
    v12 = translate_v11_event(
        {"post_type": "message", "message_type": "private", "message": "plain", "user_id": 1}
    )
    assert v12["message"] == "plain"


# ============ notice ============


def test_translate_notice_group_admin_subtype():
    assert (
        translate_v11_event(
            {"post_type": "notice", "notice_type": "group_admin", "sub_type": "set"}
        )["detail_type"]
        == "group_admin_set"
    )
    assert (
        translate_v11_event(
            {"post_type": "notice", "notice_type": "group_admin", "sub_type": "unset"}
        )["detail_type"]
        == "group_admin_unset"
    )


def test_translate_notice_group_ban_subtype():
    assert (
        translate_v11_event({"post_type": "notice", "notice_type": "group_ban", "sub_type": "ban"})[
            "detail_type"
        ]
        == "group_member_ban"
    )
    assert (
        translate_v11_event(
            {"post_type": "notice", "notice_type": "group_ban", "sub_type": "lift_ban"}
        )["detail_type"]
        == "group_member_unban"
    )


def test_translate_notice_keeps_extra_fields():
    v12 = translate_v11_event(
        {"post_type": "notice", "notice_type": "group_recall", "message_id": 88}
    )
    assert v12["detail_type"] == "group_message_delete"
    assert v12["message_id"] == 88  # 原始字段原样携带


# ============ request / meta ============


def test_translate_request():
    v12 = translate_v11_event(
        {
            "post_type": "request",
            "request_type": "group",
            "sub_type": "add",
            "user_id": 10001,
            "group_id": 20001,
            "flag": "f1",
            "comment": "hi",
        }
    )
    assert v12["type"] == "request"
    assert v12["detail_type"] == "group"
    assert v12["flag"] == "f1"
    assert v12["user_id"] == "10001"


def test_translate_meta():
    v12 = translate_v11_event(
        {"post_type": "meta_event", "meta_event_type": "heartbeat", "status": {"online": True}}
    )
    assert v12["type"] == "meta"
    assert v12["detail_type"] == "heartbeat"
    assert v12["status"] == {"online": True}


def test_translate_unknown_passthrough():
    raw = {"foo": "bar"}
    assert translate_v11_event(raw) == raw


# ============ 映射对称性 ============


def test_notice_mapping_roundtrip():
    """v11 notice_type -> v12 detail_type -> v11 notice_type 往返一致"""
    for notice_type, detail_type in {
        "friend_recall": "private_message_delete",
        "friend_add": "friend_increase",
        "group_increase": "group_member_increase",
        "group_decrease": "group_member_decrease",
        "group_recall": "group_message_delete",
        "group_upload": "group_file_upload",
        "poke": "group_poke",
    }.items():
        assert notice_type_to_detail_type(notice_type) == detail_type
        assert detail_type_to_notice_type(detail_type) == notice_type


def test_notice_mapping_subtype_defaults():
    """sub_type 缺失时的保守默认与 OneBot 12 语义一致"""
    assert notice_type_to_detail_type("group_admin") == "group_admin_unset"
    assert notice_type_to_detail_type("group_ban") == "group_member_ban"
