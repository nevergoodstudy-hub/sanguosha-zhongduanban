"""EventBus 事件总线的性质测试（Property-based）。

核心不变量：
1. 高优先级 handler 总是先于低优先级被调用
2. subscribe + unsubscribe 后，handler 不再被调用
3. publish 在 handler 抛异常时仍继续调用后续 handler
4. 事件历史记录不超过 max_history
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hypothesis import given, settings
from hypothesis import strategies as st

from game.events import EventBus, EventType, GameEvent

# ---------------------------------------------------------------------------
# 性质 1: 高优先级 handler 先调用
# ---------------------------------------------------------------------------

@given(
    priorities=st.lists(
        st.integers(min_value=-100, max_value=100),
        min_size=2,
        max_size=20,
    )
)
@settings(max_examples=200)
def test_handlers_called_in_priority_order(priorities: list[int]) -> None:
    """验证 handler 按优先级降序调用。"""
    bus = EventBus()
    call_order: list[int] = []

    for prio in priorities:
        # 使用默认参数捕获当前值
        def handler(event: GameEvent, p: int = prio) -> None:
            call_order.append(p)

        bus.subscribe(EventType.CARD_USED, handler, priority=prio)

    bus.emit(EventType.CARD_USED, message="test")

    # 调用顺序应与优先级降序一致
    expected = sorted(priorities, reverse=True)
    assert call_order == expected, (
        f"Expected order {expected}, got {call_order}"
    )


# ---------------------------------------------------------------------------
# 性质 2: unsubscribe 后 handler 不再被调用
# ---------------------------------------------------------------------------

@given(
    n_handlers=st.integers(min_value=1, max_value=10),
    remove_idx=st.data(),
)
@settings(max_examples=100)
def test_unsubscribe_removes_handler(n_handlers: int, remove_idx: st.DataObject) -> None:
    bus = EventBus()
    called: list[int] = []

    handlers = []
    for i in range(n_handlers):
        def handler(event: GameEvent, idx: int = i) -> None:
            called.append(idx)
        handlers.append(handler)
        bus.subscribe(EventType.TURN_START, handler, priority=0)

    # 随机选一个 handler 移除
    idx = remove_idx.draw(st.integers(min_value=0, max_value=n_handlers - 1))
    bus.unsubscribe(EventType.TURN_START, handlers[idx])

    bus.emit(EventType.TURN_START, message="test")

    assert idx not in called, f"Handler {idx} should not have been called after unsubscribe"
    assert len(called) == n_handlers - 1


# ---------------------------------------------------------------------------
# 性质 3: handler 异常不阻断后续 handler
# ---------------------------------------------------------------------------

@given(
    n_handlers=st.integers(min_value=2, max_value=10),
    fail_idx=st.data(),
)
@settings(max_examples=100)
def test_exception_in_handler_does_not_block_others(
    n_handlers: int, fail_idx: st.DataObject
) -> None:
    bus = EventBus()
    called: list[int] = []

    bad_idx = fail_idx.draw(st.integers(min_value=0, max_value=n_handlers - 1))

    for i in range(n_handlers):
        def handler(event: GameEvent, idx: int = i, bad: int = bad_idx) -> None:
            if idx == bad:
                raise RuntimeError("intentional test error")
            called.append(idx)

        bus.subscribe(EventType.DAMAGE_INFLICTED, handler, priority=0)

    bus.emit(EventType.DAMAGE_INFLICTED, message="test")

    # 除了出错的 handler，其余都应被调用
    assert len(called) == n_handlers - 1
    assert bad_idx not in called


# ---------------------------------------------------------------------------
# 性质 4: 事件历史不超过 max_history
# ---------------------------------------------------------------------------

@given(
    n_events=st.integers(min_value=0, max_value=300),
    max_hist=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=100)
def test_event_history_bounded(n_events: int, max_hist: int) -> None:
    bus = EventBus()
    bus._max_history = max_hist

    for _ in range(n_events):
        bus.emit(EventType.LOG_MESSAGE, message="ping")

    assert len(bus._event_history) <= max_hist


# ---------------------------------------------------------------------------
# 性质 5: clear 后不再有 handler 被调用
# ---------------------------------------------------------------------------

@given(n_handlers=st.integers(min_value=1, max_value=10))
@settings(max_examples=50)
def test_clear_removes_all_handlers(n_handlers: int) -> None:
    bus = EventBus()
    called: list[int] = []

    for i in range(n_handlers):
        def handler(event: GameEvent, idx: int = i) -> None:
            called.append(idx)
        bus.subscribe(EventType.GAME_START, handler, priority=i)

    bus.clear()
    bus.emit(EventType.GAME_START, message="test")

    assert called == [], "No handler should be called after clear()"
