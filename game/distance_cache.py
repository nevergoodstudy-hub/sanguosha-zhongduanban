"""距离计算缓存 (P2-4)

缓存玩家间距离矩阵，通过 EventBus 监听 DEATH / EQUIPMENT_EQUIPPED 等
事件自动失效。避免每次 calculate_distance 时 O(n) 遍历。

使用方式:
    cache = DistanceCache()
    cache.register_events(event_bus)
    # 查询
    dist = cache.get(p1.id, p2.id)
    if dist is None:
        dist = raw_calc(p1, p2)
        cache.set(p1.id, p2.id, dist)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .events import EventBus, GameEvent
    from .player import Player

logger = logging.getLogger(__name__)


class DistanceCache:
    """缓存玩家间距离，支持自动失效。"""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, int], int] = {}
        self._dirty: bool = True

    # ==================== 查询 / 写入 ====================

    def get(self, from_id: int, to_id: int) -> int | None:
        """查询缓存的距离，若缓存失效或未命中则返回 None。"""
        if self._dirty:
            return None
        return self._cache.get((from_id, to_id))

    def set(self, from_id: int, to_id: int, distance: int) -> None:
        """写入缓存条目。"""
        self._cache[(from_id, to_id)] = distance

    # ==================== 失效 ====================

    def invalidate(self) -> None:
        """标记缓存为脏（需要重建）。"""
        self._dirty = True
        self._cache.clear()

    def rebuild(
        self,
        players: list[Player],
        calc_fn: Callable[[Player, Player], int],
    ) -> None:
        """完全重建距离矩阵。

        Args:
            players: 所有玩家列表（含已死亡，内部自动过滤）
            calc_fn: 原始距离计算函数 (from, to) -> int
        """
        self._cache.clear()
        alive = [p for p in players if p.is_alive]
        for a in alive:
            for b in alive:
                if a is not b:
                    self._cache[(a.id, b.id)] = calc_fn(a, b)
        self._dirty = False

    # ==================== EventBus 集成 ====================

    def register_events(self, event_bus: EventBus) -> None:
        """订阅需要使缓存失效的事件。"""
        from .events import EventType

        for et in (
            EventType.DEATH,
            EventType.EQUIPMENT_EQUIPPED,
            EventType.EQUIPMENT_UNEQUIPPED,
            EventType.EQUIPMENT_EFFECT,
        ):
            event_bus.subscribe(et, self._on_invalidate)

    def _on_invalidate(self, event: GameEvent) -> None:
        """事件回调：令缓存失效。"""
        if not self._dirty:
            logger.debug("DistanceCache invalidated by event %s", event.event_type)
            self.invalidate()

    # ==================== 属性 ====================

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def size(self) -> int:
        return len(self._cache)
