"""规则系统测试 — Rule 组合、内置规则工厂、keyword 词边界优化"""

from __future__ import annotations

import asyncio

import pytest

from qingci_plugin_sdk.context import MessageContext
from qingci_plugin_sdk.ratelimit import RateLimiter
from qingci_plugin_sdk.rule import (
    Rule,
    command,
    contains,
    endswith,
    fullmatch,
    is_group,
    is_private,
    keyword,
    rate_limit,
    regex,
    startswith,
    subcommand,
    to_me,
)


def make_ctx(text: str = "", **kw) -> MessageContext:
    """构造最小可用的 MessageContext"""
    base: dict = {
        "plain_text": text,
        "message_type": "private",
        "user_id": "1",
        "group_id": "",
        "is_at_bot": False,
    }
    base.update(kw)
    return MessageContext(**base)


def run(rule: Rule, ctx: MessageContext, bot=None) -> bool:
    return asyncio.run(rule.check(bot, {}, ctx))


# ============ 文本匹配 ============


def test_startswith_sets_args_and_strips_slash():
    ctx = make_ctx("/天气 北京")
    assert run(startswith("天气"), ctx) is True
    assert ctx.args == "北京"
    ctx2 = make_ctx("天气 上海")
    assert run(startswith("天气"), ctx2) is True
    assert ctx2.args == "上海"


def test_startswith_tuple_prefixes():
    assert run(startswith(("加", "减")), make_ctx("加100")) is True
    assert run(startswith(("加", "减")), make_ctx("乘100")) is False


def test_endswith():
    assert run(endswith("好吗"), make_ctx("你好吗")) is True
    assert run(endswith("吗"), make_ctx("你好不好")) is False


def test_endswith_tuple():
    assert run(endswith(("！", "?")), make_ctx("你好?")) is True


def test_fullmatch_exact():
    assert run(fullmatch("ping"), make_ctx("ping")) is True
    assert run(fullmatch("ping"), make_ctx("pong")) is False


def test_contains_substring():
    assert run(contains("天气"), make_ctx("今天天气不错")) is True
    assert run(contains("下雨"), make_ctx("今天天气不错")) is False


def test_regex_stores_match():
    ctx = make_ctx("价格 123 元")
    assert run(regex(r"(\d+)"), ctx) is True
    assert ctx.match.group(1) == "123"


# ============ 命令 ============


def test_command_exact():
    ctx = make_ctx("/help")
    assert run(command("help"), ctx) is True
    assert ctx.command == "help"
    assert ctx.args == ""


def test_command_with_args():
    ctx = make_ctx("help  plugins")
    assert run(command("help"), ctx) is True
    assert ctx.command == "help"
    assert ctx.args == "plugins"


def test_command_aliases():
    ctx = make_ctx("/帮助")
    assert run(command(("help", "帮助")), ctx) is True
    assert ctx.command == "帮助"


def test_command_nonmatching():
    assert run(command("ban"), make_ctx("帮我一下")) is False


def test_subcommand_routes():
    # 与 command(parent) AND 组合：parent 先填 command/args，再路由子指令
    parent = command("admin")
    combined = parent & subcommand("admin", "ban")
    ctx = make_ctx("admin ban 10001")
    assert run(parent, ctx) is True
    ctx2 = make_ctx("admin ban 10001")
    assert run(combined, ctx2) is True
    assert ctx2.subcommand == "ban"
    assert ctx2.command == "admin ban"
    assert ctx2.args == "10001"


# ============ 场景 ============


def test_to_me_by_at():
    assert run(to_me(), make_ctx("hi", is_at_bot=True)) is True


def test_to_me_by_private():
    assert run(to_me(), make_ctx("hi", message_type="private")) is True


def test_to_me_group_not_at():
    assert run(to_me(), make_ctx("hi", message_type="group", is_at_bot=False)) is False


def test_is_private_and_is_group():
    assert run(is_private(), make_ctx("x", message_type="private")) is True
    assert run(is_group(), make_ctx("x", message_type="group")) is True
    assert run(is_private(), make_ctx("x", message_type="group")) is False


# ============ keyword 词边界 ============


def test_keyword_matches_plain():
    assert run(keyword("hello"), make_ctx("say hello world")) is True


def test_keyword_bounds_ascii_inside_word():
    # "helloworld" 中 "hello" 右侧紧跟 ascii 字母 => 非词边界 => 不命中
    assert run(keyword("hello"), make_ctx("helloworld")) is False
    # 左侧紧跟数字 => 非词边界
    assert run(keyword("hello"), make_ctx("4hello")) is False


def test_keyword_bounds_cjk_are_boundaries():
    assert run(keyword("hello"), make_ctx("你好hello啊")) is True


def test_keyword_start_end_of_string():
    assert run(keyword("hello"), make_ctx("hello")) is True


def test_keyword_multiple():
    r = keyword("foo", "bar")
    assert run(r, make_ctx("foo here")) is True
    assert run(r, make_ctx("a bar b")) is True
    assert run(r, make_ctx("nothing")) is False


def test_keyword_requires_at_least_one():
    with pytest.raises(ValueError):
        keyword()


# ============ 组合 ============


def test_and():
    r = is_private() & keyword("天气")
    assert run(r, make_ctx("天气", message_type="private")) is True
    # 不包含关键词
    assert run(r, make_ctx("晚安", message_type="private")) is False
    # 群聊
    assert run(r, make_ctx("天气", message_type="group")) is False


def test_or():
    r = is_private() | is_group()
    assert run(r, make_ctx("x", message_type="private")) is True
    assert run(r, make_ctx("x", message_type="group")) is True


def test_invert():
    r = ~keyword("敏感")
    assert run(r, make_ctx("普通文本")) is True
    assert run(r, make_ctx("含敏感词")) is False


def test_or_restores_ctx_before_right():
    calls = []

    def dirty_checker(bot, event, ctx):
        # 左侧污染 ctx.raw_message（默认 ""）但判定失败，右侧必须看到还原后的值
        ctx.raw_message = "被污染"
        calls.append("left")
        return False

    def right_checker(bot, event, ctx):
        calls.append("right")
        return ctx.raw_message == ""

    r = Rule(dirty_checker) | Rule(right_checker)
    ctx = make_ctx("x")
    assert run(r, ctx) is True
    assert calls == ["left", "right"]


def test_or_short_circuits_on_left_match():
    calls = []

    def left(b, e, c):
        calls.append("left")
        return True

    def right(b, e, c):
        calls.append("right")
        return True

    r = Rule(left) | Rule(right)
    assert run(r, make_ctx("x")) is True
    assert calls == ["left"]


def test_or_left_checker_exception_runs_right():
    calls = []

    def boom(b, e, ctx):
        calls.append("left")
        ctx.raw_message = "脏"
        raise RuntimeError("boom")

    def right(b, e, ctx):
        calls.append("right")
        return ctx.raw_message == ""

    r = Rule(boom) | Rule(right)
    ctx = make_ctx("x")
    # 左侧 checker 异常被 Rule.check 吞掉 -> 还原后右侧继续判定
    assert run(r, ctx) is True
    assert ctx.raw_message == ""
    assert calls == ["left", "right"]


def test_check_exception_safe_default_false():
    def boom(bot, event, ctx):
        raise RuntimeError("boom")

    r = Rule(boom)
    assert run(r, make_ctx("x")) is False


def test_async_checker_supported():
    async def async_checker(bot, event, ctx):
        return ctx.plain_text == "ok"

    assert run(Rule(async_checker), make_ctx("ok")) is True
    assert run(Rule(async_checker), make_ctx("no")) is False


# ============ rate_limit 规则（依赖 bot 桩） ============


class _FakeBotCfg:
    class _Rate:
        enabled = True

    class _Bot:
        admin_set = {"999"}
        admin_users = ["999"]
        super_admin = "0"

    rate_limit = _Rate()
    bot = _Bot()


class _FakeBot:
    config = _FakeBotCfg()
    rate_limiter = None
    connection = None


def test_rate_limit_disabled_passes_at_limit():
    bot = _FakeBot()
    bot.config.rate_limit.enabled = False
    bot.rate_limiter = RateLimiter(daily_limit=0, cooldown_seconds=0)
    assert run(rate_limit(), make_ctx("x"), bot) is True


def test_rate_limit_blocks_over_limit():
    bot = _FakeBot()
    bot.config.rate_limit.enabled = True
    bot.rate_limiter = RateLimiter(daily_limit=1, cooldown_seconds=0)
    ctx = make_ctx("x", user_id="10001")
    assert run(rate_limit(), ctx, bot) is True
    assert run(rate_limit(), ctx, bot) is False


def test_rate_limit_admin_exempt():
    bot = _FakeBot()
    bot.config.rate_limit.enabled = True
    bot.rate_limiter = RateLimiter(daily_limit=0, cooldown_seconds=0)
    ctx = make_ctx("x", user_id="999")
    assert run(rate_limit(), ctx, bot) is True


def test_rate_limit_passes_without_limiter():
    bot = _FakeBot()
    bot.rate_limiter = None
    assert run(rate_limit(), make_ctx("x"), bot) is True
