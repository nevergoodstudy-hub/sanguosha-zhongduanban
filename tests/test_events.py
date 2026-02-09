"""
事件系统单元测试
测试 EventBus、GameEvent 和相关功能
"""

import sys
from pathlib import Path

import pytest

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.events import EventBus, EventEmitter, EventType, GameEvent, get_event_bus, reset_event_bus


class TestEventBus:
    """事件总线测试"""

    def setup_method(self):
        """每个测试前重置"""
        self.bus = EventBus()
        self.received_events = []

    def test_subscribe_and_publish(self):
        """测试订阅和发布事件"""
        def handler(event):
            self.received_events.append(event)

        self.bus.subscribe(EventType.LOG_MESSAGE, handler)
        self.bus.emit(EventType.LOG_MESSAGE, message="测试消息")

        assert len(self.received_events) == 1
        assert self.received_events[0].message == "测试消息"

    def test_priority_order(self):
        """测试优先级顺序"""
        order = []

        def handler_low(event):
            order.append("low")

        def handler_high(event):
            order.append("high")

        self.bus.subscribe(EventType.GAME_START, handler_low, priority=1)
        self.bus.subscribe(EventType.GAME_START, handler_high, priority=10)

        self.bus.emit(EventType.GAME_START)

        assert order == ["high", "low"]

    def test_cancel_event(self):
        """测试取消事件"""
        def canceller(event):
            event.cancel()

        def should_not_run(event):
            self.received_events.append(event)

        self.bus.subscribe(EventType.DAMAGE_INFLICTING, canceller, priority=10)
        self.bus.subscribe(EventType.DAMAGE_INFLICTING, should_not_run, priority=1)

        event = self.bus.emit(EventType.DAMAGE_INFLICTING, damage=1)

        assert event.cancelled
        assert len(self.received_events) == 0

    def test_modify_event_data(self):
        """测试修改事件数据"""
        def modifier(event):
            event.modify_damage(5)

        self.bus.subscribe(EventType.DAMAGE_INFLICTING, modifier)

        event = self.bus.emit(EventType.DAMAGE_INFLICTING, damage=1)

        assert event.damage == 5

    def test_unsubscribe(self):
        """测试取消订阅"""
        def handler(event):
            self.received_events.append(event)

        self.bus.subscribe(EventType.LOG_MESSAGE, handler)
        self.bus.emit(EventType.LOG_MESSAGE, message="第一条")

        self.bus.unsubscribe(EventType.LOG_MESSAGE, handler)
        self.bus.emit(EventType.LOG_MESSAGE, message="第二条")

        assert len(self.received_events) == 1

    def test_global_handler(self):
        """测试全局处理器"""
        def global_handler(event):
            self.received_events.append(event)

        self.bus.subscribe_all(global_handler)

        self.bus.emit(EventType.GAME_START)
        self.bus.emit(EventType.LOG_MESSAGE, message="测试")

        assert len(self.received_events) == 2

    def test_event_history(self):
        """测试事件历史"""
        for i in range(5):
            self.bus.emit(EventType.LOG_MESSAGE, message=f"消息{i}")

        history = self.bus.get_history(3)

        assert len(history) == 3
        assert history[-1].message == "消息4"

    def test_once_fires_only_once(self):
        """测试 once() 仅触发一次"""
        def handler(event):
            self.received_events.append(event)

        self.bus.once(EventType.LOG_MESSAGE, handler)
        self.bus.emit(EventType.LOG_MESSAGE, message="第一次")
        self.bus.emit(EventType.LOG_MESSAGE, message="第二次")

        assert len(self.received_events) == 1
        assert self.received_events[0].message == "第一次"


class TestGameEvent:
    """游戏事件测试"""

    def test_event_properties(self):
        """测试事件属性"""
        event = GameEvent(
            event_type=EventType.DAMAGE_INFLICTED,
            data={
                "source": "player1",
                "target": "player2",
                "damage": 2,
                "message": "造成伤害"
            }
        )

        assert event.source == "player1"
        assert event.target == "player2"
        assert event.damage == 2
        assert event.message == "造成伤害"

    def test_cancel_and_prevent(self):
        """测试取消和阻止"""
        event = GameEvent(event_type=EventType.CARD_USING)

        assert not event.cancelled
        assert not event.prevented

        event.cancel()
        assert event.cancelled

        event.prevent()
        assert event.prevented


class TestEventEmitter:
    """事件发射器测试"""

    def test_emit_with_bus(self):
        """测试带事件总线的发射"""
        bus = EventBus()
        emitter = EventEmitter()
        emitter.set_event_bus(bus)

        received = []
        bus.subscribe(EventType.LOG_MESSAGE, lambda e: received.append(e))

        emitter.emit_log("测试日志")

        assert len(received) == 1
        assert received[0].message == "测试日志"

    def test_emit_without_bus(self):
        """测试无事件总线时的发射"""
        emitter = EventEmitter()

        # 不应抛出异常
        result = emitter.emit(EventType.LOG_MESSAGE, message="测试")
        assert result is None


class TestGlobalEventBus:
    """全局事件总线测试"""

    def setup_method(self):
        reset_event_bus()

    def test_singleton(self):
        """测试单例模式"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    def test_reset(self):
        """测试重置"""
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()

        assert bus1 is not bus2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
