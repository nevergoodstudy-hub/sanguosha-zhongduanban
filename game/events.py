"""事件总线系统
实现观察者模式，用于解耦游戏各模块
"""

from __future__ import annotations

import asyncio
import bisect
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .card import Card
    from .player import Player

logger = logging.getLogger(__name__)


class EventType(Enum):
    """游戏事件类型枚举"""

    # 回合相关
    TURN_START = auto()
    TURN_END = auto()
    ROUND_START = auto()
    ROUND_END = auto()

    # 阶段相关
    PHASE_PREPARE_START = auto()
    PHASE_PREPARE_END = auto()
    PHASE_JUDGE_START = auto()
    PHASE_JUDGE_END = auto()
    PHASE_DRAW_START = auto()
    PHASE_DRAW_END = auto()
    PHASE_PLAY_START = auto()
    PHASE_PLAY_END = auto()
    PHASE_DISCARD_START = auto()
    PHASE_DISCARD_END = auto()
    PHASE_END_START = auto()
    PHASE_END_END = auto()

    # 卡牌相关
    CARD_USED = auto()
    CARD_USING = auto()  # 使用前，可被取消
    CARD_EFFECT = auto()  # 效果生效
    CARD_DISCARDED = auto()
    CARD_DRAWN = auto()
    CARD_LOST = auto()
    CARD_OBTAINED = auto()

    # 伤害相关
    DAMAGE_INFLICTING = auto()  # 造成伤害前（可修改）
    DAMAGE_INFLICTED = auto()  # 造成伤害后
    DAMAGE_TAKEN = auto()  # 受到伤害后

    # 体力相关
    HP_CHANGED = auto()
    HP_LOST = auto()
    HP_RECOVERED = auto()
    DYING = auto()  # 濒死
    DEATH = auto()  # 死亡

    # 技能相关
    SKILL_USED = auto()
    SKILL_TRIGGERED = auto()

    # 装备相关
    EQUIPMENT_EQUIPPED = auto()
    EQUIPMENT_UNEQUIPPED = auto()
    EQUIPMENT_EFFECT = auto()  # 装备特效触发
    BEFORE_EQUIP = auto()  # 装备前（可取消）
    AFTER_EQUIP = auto()  # 装备后

    # 攻击相关
    ATTACK_TARGETING = auto()  # 指定目标时
    ATTACK_TARGETED = auto()  # 成为目标后
    ATTACK_HIT = auto()  # 命中
    ATTACK_DODGED = auto()  # 闪避

    # 判定相关
    JUDGE_START = auto()
    JUDGE_RESULT = auto()
    JUDGE_MODIFIED = auto()  # 判定被修改（如鬼才）

    # 游戏状态
    GAME_START = auto()
    GAME_END = auto()
    PLAYER_ELIMINATED = auto()

    # 日志/UI 相关
    LOG_MESSAGE = auto()
    REQUEST_INPUT = auto()
    STATE_CHANGED = auto()


@dataclass(slots=True)
class GameEvent:
    """游戏事件数据类
    携带事件的所有相关信息
    """

    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)

    # 事件控制
    cancelled: bool = False
    prevented: bool = False

    # 常用字段的快捷访问
    @property
    def source(self) -> Player | None:
        return self.data.get("source")

    @property
    def target(self) -> Player | None:
        return self.data.get("target")

    @property
    def targets(self) -> list[Player]:
        return self.data.get("targets", [])

    @property
    def card(self) -> Card | None:
        return self.data.get("card")

    @property
    def damage(self) -> int:
        return self.data.get("damage", 0)

    @property
    def message(self) -> str:
        return self.data.get("message", "")

    def cancel(self) -> None:
        """取消事件"""
        self.cancelled = True

    def prevent(self) -> None:
        """阻止事件效果"""
        self.prevented = True

    def modify_damage(self, new_damage: int) -> None:
        """修改伤害值"""
        self.data["damage"] = new_damage


# 事件处理器类型
EventHandler = Callable[[GameEvent], None]


class EventBus:
    """事件总线
    负责事件的发布和订阅

    内部存储格式: (-priority, insertion_order, handler)
    使用 bisect.insort 维护有序列表，避免每次 subscribe 全量 sort。
    """

    def __init__(self):
        # 事件处理器映射：事件类型 -> 有序 handler 列表
        # 每个元素为 (-priority, seq, handler)，按自然升序即优先级降序
        self._handlers: dict[EventType, list[tuple[int, int, EventHandler]]] = defaultdict(list)
        # 全局处理器（监听所有事件）
        self._global_handlers: list[tuple[int, int, EventHandler]] = []
        # 插入序号（用于同优先级 FIFO 稳定排序）
        self._seq: int = 0
        # 事件历史记录
        self._event_history: list[GameEvent] = []
        self._max_history: int = 100

    def _next_seq(self) -> int:
        seq = self._seq
        self._seq += 1
        return seq

    def subscribe(self, event_type: EventType, handler: EventHandler, priority: int = 0) -> None:
        """订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理器
            priority: 优先级（数字越大越先执行）
        """
        entry = (-priority, self._next_seq(), handler)
        bisect.insort(self._handlers[event_type], entry)

    def subscribe_all(self, handler: EventHandler, priority: int = 0) -> None:
        """订阅所有事件"""
        entry = (-priority, self._next_seq(), handler)
        bisect.insort(self._global_handlers, entry)

    def once(self, event_type: EventType, handler: EventHandler, priority: int = 0) -> None:
        """订阅事件（仅触发一次后自动取消订阅）"""

        def _wrapper(event: GameEvent) -> None:
            handler(event)
            self.unsubscribe(event_type, _wrapper)

        self.subscribe(event_type, _wrapper, priority)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """取消订阅"""
        self._handlers[event_type] = [
            entry for entry in self._handlers[event_type] if entry[2] != handler
        ]

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """取消订阅所有事件"""
        self._global_handlers = [entry for entry in self._global_handlers if entry[2] != handler]
        for event_type in self._handlers:
            self.unsubscribe(event_type, handler)

    def publish(self, event: GameEvent) -> GameEvent:
        """发布事件

        Args:
            event: 游戏事件

        Returns:
            处理后的事件（可能被修改或取消）
        """
        # 记录历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history :]

        # 调用全局处理器
        for _, _, handler in self._global_handlers:
            if event.cancelled:
                break
            try:
                handler(event)
            except Exception as e:
                logger.exception("[EventBus] 全局处理器异常: %s", e)

        # 调用特定事件处理器
        if not event.cancelled:
            for _, _, handler in self._handlers.get(event.event_type, []):
                if event.cancelled:
                    break
                try:
                    handler(event)
                except Exception as e:
                    logger.exception("[EventBus] 事件处理器异常 (type=%s): %s", event.event_type, e)

        return event

    def emit(self, event_type: EventType, **kwargs) -> GameEvent:
        """快捷发布事件

        Args:
            event_type: 事件类型
            **kwargs: 事件数据

        Returns:
            处理后的事件
        """
        event = GameEvent(event_type=event_type, data=kwargs)
        return self.publish(event)

    # ==================== 异步发布 ====================

    async def async_publish(self, event: GameEvent) -> GameEvent:
        """异步发布事件

        支持 sync 和 async 处理器。async handler 会被 await，
        sync handler 直接调用。与 sync publish() 完全向后兼容。

        Args:
            event: 游戏事件

        Returns:
            处理后的事件（可能被修改或取消）
        """
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history :]

        # 调用全局处理器
        for _, _, handler in self._global_handlers:
            if event.cancelled:
                break
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.exception("[EventBus] 全局处理器异常 (async): %s", e)

        # 调用特定事件处理器
        if not event.cancelled:
            for _, _, handler in self._handlers.get(event.event_type, []):
                if event.cancelled:
                    break
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.exception(
                        "[EventBus] 事件处理器异常 (async, type=%s): %s",
                        event.event_type,
                        e,
                    )

        return event

    async def async_emit(self, event_type: EventType, **kwargs) -> GameEvent:
        """快捷异步发布事件

        Args:
            event_type: 事件类型
            **kwargs: 事件数据

        Returns:
            处理后的事件
        """
        event = GameEvent(event_type=event_type, data=kwargs)
        return await self.async_publish(event)

    def clear(self) -> None:
        """清除所有订阅"""
        self._handlers.clear()
        self._global_handlers.clear()

    def get_history(self, count: int = 10) -> list[GameEvent]:
        """获取最近的事件历史"""
        return self._event_history[-count:]


class EventEmitter:
    """事件发射器混入类
    可被其他类继承以获得事件发布能力
    """

    def __init__(self):
        self._event_bus: EventBus | None = None

    def set_event_bus(self, event_bus: EventBus) -> None:
        """设置事件总线"""
        self._event_bus = event_bus

    def emit(self, event_type: EventType, **kwargs) -> GameEvent | None:
        """发布事件"""
        if self._event_bus:
            return self._event_bus.emit(event_type, **kwargs)
        return None

    def emit_log(self, message: str, **kwargs) -> None:
        """发布日志消息"""
        self.emit(EventType.LOG_MESSAGE, message=message, **kwargs)


# 单例事件总线（可选使用）
_global_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """重置全局事件总线"""
    global _global_event_bus
    _global_event_bus = None
