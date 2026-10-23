"""权限系统测试 — Permission 组合、内置权限、describe_permission"""

from __future__ import annotations

import asyncio

from qingci_plugin_sdk.context import MessageContext
from qingci_plugin_sdk.permission import (
    ADMIN,
    EVERYONE,
    GROUP,
    GROUP_MEMBER,
    MEMBER,
    PRIVATE,
    SUPERUSER,
    USER,
    Permission,
    describe_permission,
)


def make_ctx(**kw) -> MessageContext:
    base = {
        "plain_text": "x",
        "message_type": "private",
        "user_id": "1",
        "group_id": "",
    }
    base.update(kw)
    return MessageContext(**base)


def run(perm: Permission, ctx: MessageContext, bot=None) -> bool:
    return asyncio.run(perm.check(bot, {}, ctx))


# ============ 内置权限 ============


def test_everyone():
    assert run(EVERYONE, make_ctx()) is True


def test_member_is_true_permissive():
    assert run(MEMBER, make_ctx()) is True


def test_private_group():
    assert run(PRIVATE, make_ctx(message_type="private")) is True
    assert run(PRIVATE, make_ctx(message_type="group")) is False
    assert run(GROUP, make_ctx(message_type="group")) is True


def test_superuser_matches_config():
    bot = SimpleNamespaceBot(super_admin="0")
    ctx = make_ctx(user_id="0")
    assert run(SUPERUSER, ctx, bot) is True
    ctx_other = make_ctx(user_id="1")
    assert run(SUPERUSER, ctx_other, bot) is False


def test_superuser_without_config_rejected():
    assert run(SUPERUSER, make_ctx(user_id="0"), None) is False


def test_admin_in_admin_set():
    bot = SimpleNamespaceBot(admin_set={"1"})
    assert run(ADMIN, make_ctx(user_id="1"), bot) is True
    assert run(ADMIN, make_ctx(user_id="2"), bot) is False


def test_admin_fallback_to_list():
    bot = SimpleNamespaceBot(admin_set=None, admin_users=["1"])
    assert run(ADMIN, make_ctx(user_id="1"), bot) is True


def test_user_permission():
    p = USER("10001")
    assert run(p, make_ctx(user_id="10001")) is True
    assert run(p, make_ctx(user_id="10002")) is False
    # int 输入归一化后仍可匹配 str user_id
    assert run(USER(10001), make_ctx(user_id="10001")) is True


def test_group_member_only_in_group():
    p = GROUP_MEMBER("99")
    assert run(p, make_ctx(message_type="group", group_id="99")) is True
    assert run(p, make_ctx(message_type="group", group_id="98")) is False
    # 私聊一律不匹配
    assert run(p, make_ctx(message_type="private", group_id="99")) is False


# ============ 组合 ============


def test_permission_and():
    p = GROUP & USER("1")
    assert run(p, make_ctx(message_type="group", user_id="1")) is True
    assert run(p, make_ctx(message_type="group", user_id="2")) is False
    assert run(p, make_ctx(message_type="private", user_id="1")) is False


def test_permission_or():
    p = PRIVATE | GROUP
    assert run(p, make_ctx(message_type="private")) is True
    assert run(p, make_ctx(message_type="group")) is True


def test_permission_invert():
    p = ~PRIVATE
    assert run(p, make_ctx(message_type="private")) is False
    assert run(p, make_ctx(message_type="group")) is True


def test_label_composition():
    assert "&" in (GROUP & GROUP_MEMBER("1")).label
    assert "|" in (GROUP | GROUP_MEMBER("1")).label
    assert "PRIVATE" in (~PRIVATE).label


def test_check_exception_safe_false():
    def boom(bot, event, ctx):
        raise RuntimeError("boom")

    perm = Permission(boom)
    assert run(perm, make_ctx()) is False


# ============ describe ============


def test_describe_permission_label():
    assert describe_permission(SUPERUSER) == "SUPERUSER"


def test_describe_custom_default():
    assert describe_permission(Permission(lambda b, e, c: True)) == "CUSTOM"


class SimpleNamespaceBot:
    """极简 bot 桩：config.bot 提供权限元数据"""

    class _Cfg:
        pass

    class _Bot:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def __init__(self, super_admin: str = "", admin_set: set | None = None, admin_users=None):
        b = self._Bot(super_admin=super_admin, admin_set=admin_set, admin_users=admin_users)
        cfg = self._Cfg()
        cfg.bot = b
        self.config = cfg


# ---------- 组合的异常路径 ----------


def test_or_returns_false_when_left_raises():
    """左侧 checker 抛异常时按不通过处理，继续判右侧"""

    async def boom(bot, event, ctx):
        raise RuntimeError("boom")

    async def ok(bot, event, ctx):
        return True

    assert run(Permission(boom) | Permission(ok), make_ctx()) is True


def test_or_returns_false_when_right_raises():
    async def deny(bot, event, ctx):
        return False

    async def boom(bot, event, ctx):
        raise RuntimeError("boom")

    assert run(Permission(deny) | Permission(boom), make_ctx()) is False


def test_invert_returns_false_when_checker_passes():
    async def ok(bot, event, ctx):
        return True

    assert run(~Permission(ok), make_ctx()) is False


def test_admin_denied_without_bot_config():
    """bot.config 为 None 时 ADMIN 走显式拒绝分支（而非靠异常兜底）"""
    bot = type("Bot", (), {"config": None})()
    assert run(ADMIN, make_ctx(), bot=bot) is False


def test_user_permission_accepts_single_id():
    """USER 接受单个 int / str（内部统一转字符串）"""
    assert run(USER(12345), make_ctx(user_id="12345")) is True
    assert run(USER(12345), make_ctx(user_id="999")) is False
