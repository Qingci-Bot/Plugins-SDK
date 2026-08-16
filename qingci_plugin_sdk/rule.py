"""规则系统 — 插件 SDK 独立版本

支持规则组合（AND/OR/NOT），内置常用规则。
"""

import logging
import re
from typing import Callable, Union

from .context import MessageContext

logger = logging.getLogger("qingci-bot.rule")


class Rule:
    """规则对象，支持 & | ~ 组合"""

    def __init__(self, checker: Callable = None):
        self._checkers: list[Callable] = []
        if checker is not None:
            self._checkers.append(checker)

    async def check(self, bot, event: dict, ctx: MessageContext) -> bool:
        for checker in self._checkers:
            try:
                result = checker(bot, event, ctx)
                if hasattr(result, "__await__"):
                    result = await result
                if not result:
                    return False
            except Exception:
                logger.warning(f"规则 checker 异常: {checker!r}", exc_info=True)
                return False
        return True

    def __and__(self, other: "Rule") -> "Rule":
        rule = Rule()
        rule._checkers = self._checkers + other._checkers
        return rule

    def __or__(self, other: "Rule") -> "Rule":
        left = self
        right = other

        async def combined_check(bot, event, ctx) -> bool:
            fields = ("command", "args", "match")
            backup = {f: getattr(ctx, f, None) for f in fields}
            try:
                result = await left.check(bot, event, ctx)
                if result:
                    return True
                for f in fields:
                    if hasattr(ctx, f):
                        setattr(ctx, f, backup[f])
            except Exception:
                for f in fields:
                    if hasattr(ctx, f):
                        setattr(ctx, f, backup[f])
                return False
            try:
                return await right.check(bot, event, ctx)
            except Exception:
                return False

        return Rule(combined_check)

    def __invert__(self) -> "Rule":
        rule = Rule()
        original_checkers = self._checkers[:]

        async def _not_checker(bot, event, ctx):
            for c in original_checkers:
                r = c(bot, event, ctx)
                if hasattr(r, "__await__"):
                    r = await r
                if not r:
                    return True
            return False

        rule._checkers = [_not_checker]
        return rule


# ============ 内置规则工厂 ============

def startswith(prefix: Union[str, tuple[str, ...]]) -> Rule:
    """前缀匹配，匹配后自动去除前缀写入 ctx.args"""
    prefixes = (prefix,) if isinstance(prefix, str) else tuple(prefix)

    def _check(bot, event, ctx):
        text = ctx.plain_text
        for p in prefixes:
            if text.startswith(p):
                ctx.args = text[len(p):].strip()
                return True
        return False

    return Rule(_check)


def endswith(suffix: Union[str, tuple[str, ...]]) -> Rule:
    """后缀匹配"""
    suffixes = (suffix,) if isinstance(suffix, str) else tuple(suffix)
    return Rule(lambda bot, event, ctx: any(ctx.plain_text.endswith(s) for s in suffixes))


def fullmatch(text: Union[str, tuple[str, ...]]) -> Rule:
    """完全匹配"""
    texts = (text,) if isinstance(text, str) else tuple(text)
    return Rule(lambda bot, event, ctx: ctx.plain_text in texts)


def contains(keyword: str) -> Rule:
    """包含文本"""
    return Rule(lambda bot, event, ctx: keyword in ctx.plain_text)


def regex(pattern: Union[str, re.Pattern], flags: int = 0) -> Rule:
    """正则匹配，匹配后将 Match 对象存入 ctx.match"""
    compiled = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

    def _check(bot, event, ctx):
        m = compiled.search(ctx.plain_text)
        if m:
            ctx.match = m
            return True
        return False

    return Rule(_check)


def command(cmd: Union[str, tuple[str, ...]]) -> Rule:
    """命令匹配，支持别名。匹配后 ctx.command 为命令名，ctx.args 为参数"""
    commands = (cmd,) if isinstance(cmd, str) else tuple(cmd)

    def _check(bot, event, ctx):
        text = ctx.plain_text
        if text.startswith("/"):
            text_for_match = text[1:]
        else:
            text_for_match = text

        for c in commands:
            if text_for_match == c:
                ctx.command = c
                ctx.args = ""
                return True
            if text_for_match.startswith(c + " "):
                ctx.command = c
                ctx.args = text_for_match[len(c):].strip()
                return True
        return False

    return Rule(_check)


def subcommand(parent: str, sub: str) -> Rule:
    """子指令匹配

    需与 command(parent) 组合使用（AND）。匹配形式 "parent sub [args]"。
    匹配后：
    - ctx.subcommand: 子指令名
    - ctx.command:   "parent sub"
    - ctx.args:      子指令后的剩余参数（已 strip）
    """

    def _check(bot, event, ctx):
        args = getattr(ctx, "args", "")
        if args == sub:
            ctx.subcommand = sub
            ctx.command = f"{ctx.command} {sub}".strip()
            ctx.args = ""
            return True
        if args.startswith(sub + " "):
            ctx.subcommand = sub
            ctx.command = f"{ctx.command} {sub}".strip()
            ctx.args = args[len(sub):].strip()
            return True
        return False

    return Rule(_check)


def to_me() -> Rule:
    """@ 机器人或私聊"""
    def _check(bot, event, ctx):
        return ctx.is_at_bot or ctx.message_type == "private"
    return Rule(_check)


def is_private() -> Rule:
    """私聊消息"""
    return Rule(lambda bot, event, ctx: ctx.message_type == "private")


def is_group() -> Rule:
    """群聊消息"""
    return Rule(lambda bot, event, ctx: ctx.message_type == "group")


def _is_word_boundary(ch: str) -> bool:
    return not (ch.isascii() and ch.isalnum())


def keyword(*kws: str) -> Rule:
    """关键词触发规则"""
    if not kws:
        raise ValueError("至少需要一个关键词")

    async def checker(bot, event, ctx: MessageContext) -> bool:
        text = ctx.plain_text
        for kw in kws:
            idx = text.find(kw)
            while idx != -1:
                before = text[idx - 1] if idx > 0 else " "
                after = text[idx + len(kw)] if idx + len(kw) < len(text) else " "
                if _is_word_boundary(before) and _is_word_boundary(after):
                    return True
                idx = text.find(kw, idx + 1)
        return False

    return Rule(checker)


def rate_limit() -> Rule:
    """限流规则（每日上限 + 冷却间隔）

    行为约定：
    - bot.rate_limiter 为 None 或 rate_limit.enabled=False 时直接放行
    - admin_users 与 super_admin 均豁免限流
    - 拒绝时通过 bot.connection 发送提示后返回 False
    """

    async def checker(bot, event, ctx: MessageContext) -> bool:
        rl_cfg = getattr(bot.config, "rate_limit", None) if bot and bot.config else None
        limiter = getattr(bot, "rate_limiter", None) if bot else None
        if limiter is None or rl_cfg is None or not rl_cfg.enabled:
            return True
        # 管理员豁免（super_admin + admin_users 并集，O(1) 成员判断）
        admins = getattr(bot.config.bot, "admin_set", None) if bot.config else None
        if admins is not None and ctx.user_id in admins:
            return True
        ok, reason = limiter.check(ctx.user_id)
        if ok:
            return True
        try:
            connection = getattr(bot, "connection", None)
            if connection is not None and connection.is_connected:
                target = ctx.group_id if ctx.message_type == "group" else ctx.user_id
                await connection.send_msg(ctx.message_type, target, reason)
        except Exception:
            logger.warning(f"发送限流提示失败: user_id={ctx.user_id}", exc_info=True)
        return False

    return Rule(checker)