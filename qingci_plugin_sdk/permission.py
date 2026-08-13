"""权限系统 — 插件 SDK 独立版本

支持权限组合（AND/OR/NOT），内置常用权限。
权限检查基于 event + ctx，返回 bool。
"""

import logging
from typing import Callable, Union

from .context import MessageContext

logger = logging.getLogger("qingci-bot.permission")


class Permission:
    """权限对象，支持 & | ~ 组合"""

    def __init__(self, checker: Callable = None):
        self._checkers: list[Callable] = []
        if checker is not None:
            self._checkers.append(checker)

    async def check(self, bot, event: dict, ctx: MessageContext) -> bool:
        """检查权限：所有 checker 都通过才返回 True（AND 逻辑）"""
        for checker in self._checkers:
            try:
                result = checker(bot, event, ctx)
                if hasattr(result, "__await__"):
                    result = await result
                if not result:
                    return False
            except Exception:
                logger.warning(f"权限 checker 异常: {checker!r}", exc_info=True)
                return False
        return True

    def __and__(self, other: "Permission") -> "Permission":
        perm = Permission()
        perm._checkers = self._checkers + other._checkers
        return perm

    def __or__(self, other: "Permission") -> "Permission":
        left = self
        right = other

        async def combined_check(bot, event, ctx) -> bool:
            try:
                if await left.check(bot, event, ctx):
                    return True
            except Exception:
                return False
            try:
                return await right.check(bot, event, ctx)
            except Exception:
                return False

        return Permission(combined_check)

    def __invert__(self) -> "Permission":
        perm = Permission()
        original_checkers = self._checkers[:]

        async def _not_checker(bot, event, ctx):
            for c in original_checkers:
                r = c(bot, event, ctx)
                if hasattr(r, "__await__"):
                    r = await r
                if not r:
                    return True
            return False

        perm._checkers = [_not_checker]
        return perm


# ============ 内置权限 ============

EVERYONE = Permission(lambda bot, event, ctx: True)
"""所有人"""


async def _is_superuser(bot, event, ctx):
    admin_users = bot.config.bot.admin_users if bot and bot.config else []
    return ctx.user_id in admin_users


SUPERUSER = Permission(_is_superuser)
"""超级管理员（配置中的 admin_users）"""

ADMIN = Permission(_is_superuser)
"""管理员（与 SUPERUSER 等价但独立实例）"""


def _is_private(bot, event, ctx):
    return ctx.message_type == "private"


def _is_group(bot, event, ctx):
    return ctx.message_type == "group"


PRIVATE = Permission(_is_private)
"""私聊消息"""

GROUP = Permission(_is_group)
"""群聊消息"""

MEMBER = Permission(lambda bot, event, ctx: True)
"""普通群员（与 EVERYONE 等价但独立实例）"""


def USER(user_ids: Union[int, list[int]]) -> Permission:
    """指定用户可用"""
    ids = [user_ids] if isinstance(user_ids, int) else list(user_ids)
    return Permission(lambda bot, event, ctx: ctx.user_id in ids)


def GROUP_MEMBER(group_ids: Union[int, list[int]]) -> Permission:
    """指定群的成员可用（仅群聊消息生效）

    参数为群号列表；私聊消息一律不匹配。
    """
    ids = [group_ids] if isinstance(group_ids, int) else list(group_ids)
    return Permission(
        lambda bot, event, ctx: ctx.message_type == "group" and ctx.group_id in ids
    )