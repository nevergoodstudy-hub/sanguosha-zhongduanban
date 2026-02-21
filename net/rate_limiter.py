"""Token Bucket 速率限制器

用于游戏动作的精细速率控制。与 security.py 中的滑动窗口
限制器互补：滑动窗口控制整体消息吞吐，Token Bucket 控制
游戏动作频率（允许短时突发但限制持续速率）。
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class TokenBucket:
    """令牌桶速率限制器

    以固定速率产生令牌，允许一定的突发流量。

    Args:
        rate: 每秒产生的令牌数
        burst: 桶的最大容量（允许的最大突发量）
    """

    def __init__(self, rate: float = 10.0, burst: int = 20) -> None:
        self.rate = rate
        self.burst = burst
        self.tokens: float = float(burst)
        self.last_refill: float = time.monotonic()

    def consume(self, n: int = 1) -> bool:
        """尝试消耗 n 个令牌

        Args:
            n: 需要消耗的令牌数

        Returns:
            True 表示允许（有足够令牌），False 表示拒绝
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now

        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    @property
    def available(self) -> float:
        """当前可用令牌数（不消耗）"""
        now = time.monotonic()
        elapsed = now - self.last_refill
        return min(self.burst, self.tokens + elapsed * self.rate)


class ConnectionRateLimiter:
    """基于连接 ID 的速率限制管理器

    为每个连接维护独立的 TokenBucket 实例。
    """

    def __init__(self, rate: float = 10.0, burst: int = 20) -> None:
        self._rate = rate
        self._burst = burst
        self._buckets: dict[str, TokenBucket] = {}

    def check(self, conn_id: str) -> bool:
        """检查连接是否允许发送消息

        Args:
            conn_id: 连接标识符

        Returns:
            True 表示允许，False 表示被限流
        """
        if conn_id not in self._buckets:
            self._buckets[conn_id] = TokenBucket(self._rate, self._burst)
        return self._buckets[conn_id].consume()

    def remove(self, conn_id: str) -> None:
        """移除连接的限流桶（断开连接时调用）"""
        self._buckets.pop(conn_id, None)

    @property
    def active_connections(self) -> int:
        """当前跟踪的连接数"""
        return len(self._buckets)
