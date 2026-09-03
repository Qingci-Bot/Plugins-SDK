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


def test_max_entries_bounds_memory_and_evicts_oldest():

    limiter = RateLimiter(daily_limit=1, cooldown_seconds=0, max_entries=3)
    # 依次访问 4 个用户，达到上限后最早活动者被淘汰
    limiter.check("u1")
    limiter.check("u2")
    limiter.check("u3")
    assert len(limiter._data) == 3
    # u1 最早活动，写入 u4 时应被淘汰
    limiter.check("u4")
    assert "u1" not in limiter._data
    assert len(limiter._data) == 3
    assert "u4" in limiter._data


def test_evict_skips_recently_updated_oldest():
    import time

    limiter = RateLimiter(daily_limit=5, cooldown_seconds=0, max_entries=2)
    limiter.check("a")
    limiter.check("b")
    time.sleep(0.01)
    # 刷新 a 的活动时间，让 a 不再是"最旧"
    limiter.check("a")
    assert len(limiter._data) == 2
    limiter.check("c")  # 应淘汰 b（a 的活动时间更近）
    assert "b" not in limiter._data
    assert "a" in limiter._data


def test_max_entries_default_is_large():
    # 默认上限不允许小规模访问触发淘汰
    limiter = RateLimiter()
    for i in range(1000):
        assert limiter.check(str(i))[0] is True
    assert len(limiter._data) == 1000
