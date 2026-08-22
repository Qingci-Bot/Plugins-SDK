"""RateLimiter 用户级限流器测试

跨协议一致性：事件链中 user_id 统一为 str，限流器按 str 键存储，
同时兼容调用方传入 int（自动 str 化）。
"""

from __future__ import annotations

from qingci_plugin_sdk.ratelimit import RateLimiter


def test_str_and_int_keys_hit_same_bucket():
    limiter = RateLimiter(daily_limit=2, cooldown_seconds=0)
    assert limiter.check("10001") == (True, "")
    # int 与 str 同键命中同一计数桶
    assert limiter.check(10001)[0] is True
    ok, reason = limiter.check("10001")
    assert ok is False
    assert "上限" in reason


def test_cooldown_blocks_repeated_calls():
    limiter = RateLimiter(daily_limit=10, cooldown_seconds=3600)
    assert limiter.check("10001")[0] is True
    ok, reason = limiter.check("10001")
    assert ok is False
    assert "太快" in reason


def test_daily_limit_resets_on_new_day(monkeypatch):
    import datetime as _dt

    from qingci_plugin_sdk import ratelimit as ratelimit_module

    class _StubDate:
        """替身 date 类：today() 返回可控目标日期（ratelimit 用 date.today()）"""

        _target = _dt.date(2026, 8, 22)

        @classmethod
        def today(cls):
            return cls._target

    monkeypatch.setattr(ratelimit_module, "date", _StubDate)
    limiter = RateLimiter(daily_limit=1, cooldown_seconds=0)
    assert limiter.check("10001")[0] is True
    assert limiter.check("10001")[0] is False

    # 次日重置
    _StubDate._target = _dt.date(2026, 8, 23)
    assert limiter.check("10001")[0] is True
