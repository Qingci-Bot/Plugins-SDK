"""用户级限流器 — 插件 SDK 独立版本"""

import time
from datetime import date


class RateLimiter:
    """基于内存 dict 的限流器：{user_id: (日期字符串, 当日计数, 上次成功时间戳)}"""

    def __init__(self, daily_limit: int = 50, cooldown_seconds: int = 10):
        self.daily_limit = daily_limit
        self.cooldown_seconds = cooldown_seconds
        # 事件链中 user_id 统一为 str（v12 模型字符串化），键按 str 存储
        self._data: dict[str, tuple[str, int, float]] = {}

    def check(self, user_id: str | int) -> tuple[bool, str]:
        """检查用户是否允许本次调用

        Args:
            user_id: 用户 ID（str / int 均可，统一按 str 存储）

        Returns:
            (ok, reason): ok 为 True 时放行并计数；为 False 时 reason 为提示文案
        """
        key = str(user_id)
        now = time.time()
        today = date.today().isoformat()
        record = self._data.get(key)

        if record is None or record[0] != today:
            count = 0
            last_ts = 0.0
        else:
            count = record[1]
            last_ts = record[2]

        if count >= self.daily_limit:
            return False, f"今日调用次数已达上限（{self.daily_limit} 次），请明天再试。"

        if self.cooldown_seconds > 0 and last_ts and now - last_ts < self.cooldown_seconds:
            return False, f"发送太快啦，请 {self.cooldown_seconds} 秒后再试。"

        self._data[key] = (today, count + 1, now)
        return True, ""

    def cleanup(self, inactive_days: int = 7) -> int:
        """清理超过 inactive_days 天未活跃的条目，返回清理条数"""
        cutoff = time.time() - inactive_days * 86400
        stale = [uid for uid, (_, _, ts) in self._data.items() if ts < cutoff]
        for uid in stale:
            del self._data[uid]
        return len(stale)
