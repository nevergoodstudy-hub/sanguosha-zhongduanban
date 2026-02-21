"""Tests for async EventBus methods (async_publish / async_emit)."""

import pytest

from game.events import EventBus, EventType, GameEvent


@pytest.mark.asyncio
async def test_async_emit_calls_sync_handler():
    bus = EventBus()
    results = []

    def handler(event: GameEvent) -> None:
        results.append(event.event_type)

    bus.subscribe(EventType.TURN_START, handler)
    event = await bus.async_emit(EventType.TURN_START, player="test")
    assert results == [EventType.TURN_START]
    assert event.data["player"] == "test"


@pytest.mark.asyncio
async def test_async_emit_calls_async_handler():
    bus = EventBus()
    results = []

    async def handler(event: GameEvent) -> None:
        results.append(event.event_type)

    bus.subscribe(EventType.CARD_USED, handler)
    await bus.async_emit(EventType.CARD_USED)
    assert results == [EventType.CARD_USED]


@pytest.mark.asyncio
async def test_async_emit_mixed_handlers():
    bus = EventBus()
    order = []

    def sync_handler(event: GameEvent) -> None:
        order.append("sync")

    async def async_handler(event: GameEvent) -> None:
        order.append("async")

    bus.subscribe(EventType.DAMAGE_TAKEN, sync_handler, priority=10)
    bus.subscribe(EventType.DAMAGE_TAKEN, async_handler, priority=5)
    await bus.async_emit(EventType.DAMAGE_TAKEN)
    assert order == ["sync", "async"]


@pytest.mark.asyncio
async def test_async_publish_respects_cancel():
    bus = EventBus()
    results = []

    def canceller(event: GameEvent) -> None:
        event.cancel()

    def after(event: GameEvent) -> None:
        results.append("should_not_run")

    bus.subscribe(EventType.HP_CHANGED, canceller, priority=10)
    bus.subscribe(EventType.HP_CHANGED, after, priority=5)
    event = await bus.async_emit(EventType.HP_CHANGED)
    assert event.cancelled is True
    assert results == []


@pytest.mark.asyncio
async def test_async_publish_global_handler():
    bus = EventBus()
    results = []

    async def global_handler(event: GameEvent) -> None:
        results.append(event.event_type)

    bus.subscribe_all(global_handler)
    await bus.async_emit(EventType.GAME_START)
    await bus.async_emit(EventType.GAME_END)
    assert results == [EventType.GAME_START, EventType.GAME_END]


@pytest.mark.asyncio
async def test_async_publish_records_history():
    bus = EventBus()
    await bus.async_emit(EventType.TURN_START)
    await bus.async_emit(EventType.TURN_END)
    history = bus.get_history(10)
    assert len(history) == 2
    assert history[0].event_type == EventType.TURN_START
    assert history[1].event_type == EventType.TURN_END


@pytest.mark.asyncio
async def test_async_publish_handler_exception_doesnt_crash():
    bus = EventBus()
    results = []

    async def bad_handler(event: GameEvent) -> None:
        raise ValueError("boom")

    def good_handler(event: GameEvent) -> None:
        results.append("ok")

    bus.subscribe(EventType.SKILL_USED, bad_handler, priority=10)
    bus.subscribe(EventType.SKILL_USED, good_handler, priority=5)
    # Should not raise, and good_handler should still run
    await bus.async_emit(EventType.SKILL_USED)
    assert results == ["ok"]


@pytest.mark.asyncio
async def test_async_emit_returns_event():
    bus = EventBus()
    event = await bus.async_emit(EventType.CARD_DRAWN, count=2)
    assert isinstance(event, GameEvent)
    assert event.event_type == EventType.CARD_DRAWN
    assert event.data["count"] == 2
