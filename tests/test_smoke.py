"""Plugins-SDK 冒烟测试 — 验证核心导出与基础行为（零外部依赖）

保证 SDK 作为独立包可安装、可导入，核心协议对象（PluginBase /
Matcher / Rule / MessageContext / 类型化事件 / i18n / llm_tool）
的基本行为正确，防止协议层回归。
"""

import qingci_plugin_sdk as sdk
from qingci_plugin_sdk import (
    EVERYONE,
    GroupIncreaseNotice,
    I18n,
    MessageContext,
    MessageEditedEvent,
    PluginBase,
    PluginStatus,
    llm_tool,
    on_startswith,
    parse_event,
    parse_notice_event,
    startswith,
)


def test_version():
    assert isinstance(sdk.__version__, str)
    parts = sdk.__version__.split(".")
    assert len(parts) >= 2
    assert all(p.isdigit() for p in parts)


def test_plugin_base_instantiation():
    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    assert p.name == "demo"
    assert p.status == PluginStatus.LOADING  # 初始过渡态
    assert p.enabled is True  # LOADING 视为启用（向后兼容）
    # LOADED → 禁用 → 恢复
    p._status = PluginStatus.LOADED
    p.enabled = False
    assert p.status == PluginStatus.DISABLED
    assert p.enabled is False
    p.enabled = True
    assert p.status == PluginStatus.LOADED


def test_register_api_records_registration():
    """register_api：规范化 path/methods 并写入 _apis（供主项目挂载）"""

    class DemoPlugin(PluginBase):
        name = "demo"

        async def on_load(self):
            pass

        async def on_unload(self):
            pass

    p = DemoPlugin()
    p.register_api("checkin-ranking", lambda req: {}, methods=["GET"], description="排行")
    p.register_api("/content-safety/terms/add", lambda req: {}, methods=["post"])
    p.register_api("raw", lambda req: {})

    assert len(p._apis) == 3
    first = p._apis[0]
    assert first["path"] == "checkin-ranking"  # 去除首尾斜杠
    assert first["methods"] == ["GET"]
    assert first["description"] == "排行"
    assert callable(first["handler"])
    # methods 大小写归一化；缺省为 GET
    assert p._apis[1]["methods"] == ["POST"]
    assert p._apis[1]["path"] == "content-safety/terms/add"
    assert p._apis[2]["methods"] == ["GET"]


def test_message_context_basics():
    ctx = MessageContext(
        message_type="group",
        user_id=100,
        group_id=200,
        raw_message="你好",
        sender={"nickname": "Alice", "card": ""},
    )
    assert ctx.sender_name == "Alice"
    assert ctx.platform == "onebot"  # 默认平台


async def test_startswith_rule_matches():
    rule = startswith("你好")
    ctx = MessageContext(raw_message="你好世界", plain_text="你好世界")
    assert await rule.check(None, {}, ctx) is True
    assert ctx.args == "世界"  # 前缀被去除写入 args


async def test_startswith_rule_rejects():
    rule = startswith("你好")
    ctx = MessageContext(raw_message="hello world", plain_text="hello world")
    assert await rule.check(None, {}, ctx) is False


def test_on_startswith_builds_matcher():
    def handler(ctx):
        return "pong"

    matcher = on_startswith("ping")(handler)
    assert matcher.handler is handler
    assert matcher.event_type == "message"
    assert matcher.permission == EVERYONE
    assert matcher.block is True


def test_parse_notice_group_increase():
    raw = {
        "post_type": "notice",
        "notice_type": "group_increase",
        "time": 1786889000,
        "self_id": 1,
        "user_id": 100,
        "group_id": 200,
        "sub_type": "approve",
    }
    ev = parse_notice_event(raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert ev.user_id == 100
    assert ev.group_id == 200
    assert ev.sub_type == "approve"


def test_parse_event_router():
    raw = {"post_type": "notice", "notice_type": "group_increase", "user_id": 1}
    ev = parse_event("notice", raw)
    assert isinstance(ev, GroupIncreaseNotice)
    assert parse_event("meta", raw) is None  # 未知类型返回 None


def test_parse_message_edited_event():
    """v12 message_edited → MessageEditedEvent（str/bool 字段类型化保留）"""
    raw = {
        "type": "notice",
        "detail_type": "message_edited",
        "sub_type": "friend",
        "id": "evt-7",
        "impl": "telegram",
        "platform": "telegram",
        "self_id": "30001",
        "time": 1786889000,
        "user_id": "10001",
        "group_id": "",
        "message_id": "42",
        "alt_message": "改后的内容",
        "message": [{"type": "text", "data": {"text": "改后的内容"}}],
        "is_at_bot": False,
    }
    ev = parse_notice_event(raw)
    assert isinstance(ev, MessageEditedEvent)
    assert ev.notice_type == "message_edited"
    assert ev.detail_type == "message_edited"
    assert ev.user_id == 10001
    assert ev.message_id == "42"  # str 字段原样保留（非 int）
    assert ev.alt_message == "改后的内容"
    assert ev.message[0]["type"] == "text"
    assert ev.is_at_bot is False  # bool 字段原样保留
    assert ev.platform == "telegram"


def test_parse_unknown_notice_falls_back_to_base():
    """未知 detail_type 仍回退 NoticeEvent 基类（不抛异常）"""
    raw = {"type": "notice", "detail_type": "group_message_react", "user_id": 1}
    ev = parse_notice_event(raw)
    assert type(ev).__name__ == "NoticeEvent"
    assert ev.notice_type == "group_message_react"  # 未知类型原样映射


def test_i18n_translate():
    i18n = I18n(translations={"hello": "你好"})
    assert i18n.t("hello") == "你好"
    assert i18n.t("missing") == "missing"  # 缺失 key 原样返回
    assert I18n(translations={"greet": "你好，{name}"}).t("greet", name="世界") == "你好，世界"


def test_llm_tool_decorator():
    @llm_tool(description="加法")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(1, 2) == 3  # 装饰器不改原函数行为
    from qingci_plugin_sdk.llm_tool import begin_tool_collection, end_tool_collection

    specs = begin_tool_collection()
    try:

        @llm_tool(description="乘法")
        def mul(a: int, b: int) -> int:
            return a * b

    finally:
        end_tool_collection()
    assert any(s.handler is mul for s in specs)
    assert any(s.description == "乘法" for s in specs)
