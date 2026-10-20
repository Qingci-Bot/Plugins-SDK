"""用户级限流器 — 插件 SDK 独立版本"""

import time
from collections import OrderedDict
from datetime import date


class RateLimiter:
    """基于内存 dict 的限流器：{user_id: (日期字符串, 当日计数, 上次成功时间戳)}

    内部用 OrderedDict 维护「最近成功调用」顺序（LRU），容量触顶时 O(1)
    淘汰最久未活动者，避免洪泛场景下 O(n) 扫描退化为 O(n²)。
    """

    def __init__(
        self,
        daily_limit: int = 50,
        cooldown_seconds: int = 10,
        *,
        max_entries: int = 100000,
    ):
        self.daily_limit = daily_limit
        self.cooldown_seconds = cooldown_seconds
        # 容量上限：防长期运行内存无界膨胀。仅在「新键写入」且已触顶时淘汰
        # 最久未活动者（对冲大集群 / 脏键堆积）；max_entries <= 0 表示不设上限。
        self.max_entries = max_entries
        # 事件链中 user_id 统一为 str（v12 模型字符串化），键按 str 存储
        self._data: OrderedDict[str, tuple[str, int, float]] = OrderedDict()

    def _evict_oldest(self) -> None:
        """淘汰最久未活动的键以守住容量上限（OrderedDict 头部即最旧）"""
        if self._data:
            self._data.popitem(last=False)

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

        # 触顶且为「新键」时才淘汰最久未活动者。已有键的重复调用（含被限流
        # 拒绝的调用）不得驱逐他人，否则单个高频用户反复 check 即可逐条清空
        # 整张表，限流失效。
        if record is None and self.max_entries > 0 and len(self._data) >= self.max_entries:
            self._evict_oldest()

        if count >= self.daily_limit:
            return False, f"今日调用次数已达上限（{self.daily_limit} 次），请明天再试。"

        if self.cooldown_seconds > 0 and last_ts and now - last_ts < self.cooldown_seconds:
            return False, f"发送太快啦，请 {self.cooldown_seconds} 秒后再试。"

        self._data[key] = (today, count + 1, now)
        # 刷新活动顺序：最近成功调用者移到尾部，头部即最久未活动者（O(1)）
        self._data.move_to_end(key)
        return True, ""

    def cleanup(self, inactive_days: int = 7) -> int:
        """清理超过 inactive_days 天未活跃的条目，返回清理条数"""
        cutoff = time.time() - inactive_days * 86400
        stale = [uid for uid, (_, _, ts) in self._data.items() if ts < cutoff]
        for uid in stale:
            del self._data[uid]
        return len(stale)
