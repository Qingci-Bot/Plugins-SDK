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


def test_repeated_check_of_existing_key_does_not_evict_others():
    """容量触顶时已有键的重复调用不得驱逐他人

    回归：此前淘汰发生在「判断键是否存在」之前，单个高频用户反复 check
    即可逐条清空整张限流表。
    """
    limiter = RateLimiter(daily_limit=100, cooldown_seconds=0, max_entries=3)
    for uid in ("u1", "u2", "u3"):
        limiter.check(uid)
    for _ in range(5):
        limiter.check("u1")
    assert set(limiter._data) == {"u1", "u2", "u3"}


def test_rejected_check_does_not_evict_others():
    """被限流拒绝的调用同样不得触发淘汰"""
    limiter = RateLimiter(daily_limit=1, cooldown_seconds=0, max_entries=2)
    limiter.check("a")
    limiter.check("b")
    ok, _ = limiter.check("a")  # 超当日上限，被拒
    assert ok is False
    assert set(limiter._data) == {"a", "b"}


def test_evict_oldest_on_empty_table_is_noop():
    """空表淘汰不应抛异常（宿主可能在容量边界反复触发）"""
    limiter = RateLimiter(daily_limit=1, cooldown_seconds=0, max_entries=1)
    limiter._evict_oldest()
    assert limiter._data == {}


def test_cleanup_removes_only_inactive_entries():
    import time as _time

    limiter = RateLimiter(daily_limit=10, cooldown_seconds=0)
    limiter.check("stale")
    limiter.check("fresh")

    # 把 stale 的最后活跃时间改到 8 天前
    today, count, _ = limiter._data["stale"]
    limiter._data["stale"] = (today, count, _time.time() - 8 * 86400)

    assert limiter.cleanup(inactive_days=7) == 1
    assert "stale" not in limiter._data
    assert "fresh" in limiter._data


def test_cleanup_without_stale_entries_returns_zero():
    limiter = RateLimiter(daily_limit=10, cooldown_seconds=0)
    limiter.check("u1")
    assert limiter.cleanup(inactive_days=7) == 0
