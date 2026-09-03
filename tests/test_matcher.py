"""匹配器系统测试 — Matcher 工厂、MatcherContext、模块级收集"""

from __future__ import annotations

from qingci_plugin_sdk.context import MessageContext
from qingci_plugin_sdk.matcher import (
    MatcherContext,
    begin_module_collection,
    end_module_collection,
    on_command,
    on_keyword,
    on_message,
    on_notice,
    on_request,
    on_startswith,
)

# ============ Matcher 工厂 ============


def test_on_message_decorator_builds_matcher():
    @on_message(priority=5, block=False, description="测试")
    async def handler(ctx):
        return "hi"

    assert isinstance(handler, object)
    assert handler.event_type == "message"
    assert handler.priority == 5
    assert handler.block is False
    assert handler.meta["description"] == "测试"


def test_on_command_meta_and_aliases():
    @on_command("help", aliases=("h", "帮助"), description="帮助")
    async def help_cmd(ctx):
        return "help"

    assert help_cmd.meta["command"] == "help"
    assert help_cmd.meta["aliases"] == ["h", "帮助"]
    assert help_cmd.meta["hidden_in_help"] is False


def test_on_command_aliases_included_in_cmd_list():
    @on_command(("ping",), aliases=("p",))
    async def ping(ctx):
        return "pong"

    assert ping.meta["command"] == "ping"
    assert ping.meta["aliases"] == ["p"]


def test_on_command_subcommands_build_sub_matchers():
    async def ban(ctx):
        return "banned"

    @on_command("admin", subcommands={"ban": ban})
    async def admin(ctx):
        return "admin"

    subs = admin.meta["sub_matchers"]
    assert len(subs) == 1
    assert subs[0].meta["command"] == "admin ban"
    assert subs[0].meta["is_subcommand"] is True


def test_on_command_args_schema_stored():
    @on_command("weather", args_schema={"city": str, "days": int})
    async def weather(ctx, city="", days=1):
        return city

    assert weather.meta["args_schema"] == {"city": str, "days": int}


def test_on_startswith_event_type():
    @on_startswith("天气", description="天气")
    async def weather(ctx):
        return ""

    assert weather.event_type == "message"
    assert weather.meta["description"] == "天气"


def test_on_keyword_event_type():
    @on_keyword(("签到", "打卡"))
    async def checkin(ctx):
        return ""

    assert checkin.event_type == "message"


def test_on_notice_and_request_event_types():
    @on_notice()
    async def on_card(ctx):
        return ""

    @on_request()
    async def on_friend_req(ctx):
        return ""

    assert on_card.event_type == "notice"
    assert on_friend_req.event_type == "request"


# ============ MatcherContext ============


def test_matcher_context_inherits_message_context():
    base = MessageContext(plain_text="hi", message_type="group", user_id="1", group_id="9")
    mc = MatcherContext.from_message_context(base, bot=object(), matcher=object())
    assert mc.plain_text == "hi"
    assert mc.message_type == "group"
    assert mc.user_id == "1"
    assert mc.bot is not None
    assert mc.matcher is not None


def test_matcher_context_defaults():
    mc = MatcherContext()
    assert mc.command == ""
    assert mc.args == ""
    assert mc.parsed_args == {}


# ============ 模块级收集 ============


def test_module_collection_collects_matchers():
    collected = begin_module_collection()
    try:

        @on_command("cmd")
        async def cmd(ctx):
            return ""

        @on_message()
        async def msg(ctx):
            return ""

        assert len(collected) == 2
    finally:
        end_module_collection()


def test_no_collection_when_collector_inactive():
    # 不开启收集时，on_message 不应污染任何全局列表（返回的 matcher 由调用方持有）
    begin_module_collection()
    end_module_collection()  # 确保干净

    @on_message()
    async def solo(ctx):
        return ""

    assert solo.event_type == "message"
