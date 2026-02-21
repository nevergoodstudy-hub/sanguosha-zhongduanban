"""Distance calculation cache tests (P2-4)."""

import pytest

from game.distance_cache import DistanceCache
from game.events import EventBus, EventType, GameEvent


class _FakePlayer:
    """Minimal player stub for cache tests."""

    def __init__(self, pid: int, alive: bool = True):
        self.id = pid
        self.is_alive = alive


class TestDistanceCache:
    """Test DistanceCache."""

    def test_initially_dirty(self):
        cache = DistanceCache()
        assert cache.is_dirty is True
        assert cache.get(0, 1) is None

    def test_set_and_get(self):
        cache = DistanceCache()
        cache._dirty = False
        cache.set(0, 1, 3)
        assert cache.get(0, 1) == 3
        assert cache.get(1, 0) is None  # directional

    def test_invalidate_clears_cache(self):
        cache = DistanceCache()
        cache._dirty = False
        cache.set(0, 1, 2)
        cache.invalidate()
        assert cache.is_dirty is True
        assert cache.get(0, 1) is None
        assert cache.size == 0

    def test_rebuild(self):
        cache = DistanceCache()
        p0 = _FakePlayer(0)
        p1 = _FakePlayer(1)
        p2 = _FakePlayer(2, alive=False)

        def calc(a, b):
            return abs(a.id - b.id)

        cache.rebuild([p0, p1, p2], calc)
        assert cache.is_dirty is False
        assert cache.get(0, 1) == 1
        assert cache.get(1, 0) == 1
        # Dead player excluded
        assert cache.get(0, 2) is None

    def test_event_invalidation(self):
        cache = DistanceCache()
        bus = EventBus()
        cache.register_events(bus)

        # Build cache
        cache._dirty = False
        cache.set(0, 1, 5)
        assert cache.get(0, 1) == 5

        # Fire DEATH event → cache should invalidate
        bus.emit(EventType.DEATH, target=None, source=None)
        assert cache.is_dirty is True
        assert cache.get(0, 1) is None

    def test_equipment_event_invalidation(self):
        cache = DistanceCache()
        bus = EventBus()
        cache.register_events(bus)

        cache._dirty = False
        cache.set(1, 2, 3)

        bus.emit(EventType.EQUIPMENT_EQUIPPED, player=None, card=None)
        assert cache.is_dirty is True

    def test_double_invalidation_is_noop(self):
        """Invalidating an already-dirty cache should not error."""
        cache = DistanceCache()
        cache.invalidate()
        cache.invalidate()
        assert cache.is_dirty is True

    def test_rebuild_with_single_player(self):
        cache = DistanceCache()
        p0 = _FakePlayer(0)
        cache.rebuild([p0], lambda a, b: 0)
        assert cache.is_dirty is False
        assert cache.size == 0

    def test_size_after_rebuild(self):
        cache = DistanceCache()
        players = [_FakePlayer(i) for i in range(4)]
        cache.rebuild(players, lambda a, b: 1)
        # 4 alive players → 4*3 = 12 pairs
        assert cache.size == 12
