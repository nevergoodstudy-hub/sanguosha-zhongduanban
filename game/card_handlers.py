# -*- coding: utf-8 -*-
"""
卡牌处理器模块
负责注册和管理各类卡牌的处理逻辑

本模块将卡牌处理逻辑从 GameEngine 中解耦，
使用注册表模式支持扩展性更强的卡牌系统。
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum, auto

if TYPE_CHECKING:
    from .engine import GameEngine
    from .player import Player
    from .card import Card


class CardHandlerType(Enum):
    """卡牌处理器类型"""
    BASIC = auto()          # 基本牌（杀、闪、桃）
    TRICK = auto()          # 普通锦囊
    DELAY_TRICK = auto()    # 延时锦囊
    EQUIPMENT = auto()      # 装备牌


@dataclass
class CardHandlerInfo:
    """卡牌处理器信息"""
    card_name: str
    handler_type: CardHandlerType
    handler: Callable
    requires_target: bool = False
    target_count: int = 1  # 0 = 无目标，1 = 单目标，-1 = 多目标


class CardHandlerRegistry:
    """
    卡牌处理器注册表

    用于注册和查找卡牌的处理函数，
    支持动态注册新的卡牌类型。
    """

    def __init__(self):
        self._handlers: Dict[str, CardHandlerInfo] = {}

    def register(
        self,
        card_name: str,
        handler: Callable,
        handler_type: CardHandlerType = CardHandlerType.BASIC,
        requires_target: bool = False,
        target_count: int = 1
    ) -> None:
        """
        注册卡牌处理器

        Args:
            card_name: 卡牌名称
            handler: 处理函数
            handler_type: 处理器类型
            requires_target: 是否需要目标
            target_count: 目标数量
        """
        self._handlers[card_name] = CardHandlerInfo(
            card_name=card_name,
            handler=handler,
            handler_type=handler_type,
            requires_target=requires_target,
            target_count=target_count
        )

    def get_handler(self, card_name: str) -> Optional[Callable]:
        """获取卡牌处理器"""
        info = self._handlers.get(card_name)
        return info.handler if info else None

    def get_handler_info(self, card_name: str) -> Optional[CardHandlerInfo]:
        """获取卡牌处理器信息"""
        return self._handlers.get(card_name)

    def has_handler(self, card_name: str) -> bool:
        """检查是否有对应处理器"""
        return card_name in self._handlers

    def list_handlers(self, handler_type: Optional[CardHandlerType] = None) -> List[str]:
        """
        列出所有已注册的卡牌名称

        Args:
            handler_type: 筛选特定类型，None 则返回所有

        Returns:
            卡牌名称列表
        """
        if handler_type is None:
            return list(self._handlers.keys())
        return [
            name for name, info in self._handlers.items()
            if info.handler_type == handler_type
        ]


def init_default_handlers(registry: CardHandlerRegistry, engine: 'GameEngine') -> None:
    """
    初始化默认的卡牌处理器

    将 GameEngine 中的处理方法注册到注册表

    Args:
        registry: 处理器注册表
        engine: 游戏引擎实例
    """
    from .card import CardName

    # 基本牌
    registry.register(
        CardName.SHA, engine._use_sha,
        CardHandlerType.BASIC, requires_target=True
    )
    registry.register(
        CardName.TAO, engine._use_tao,
        CardHandlerType.BASIC, requires_target=False
    )

    # 普通锦囊
    registry.register(
        CardName.JUEDOU, engine._use_juedou,
        CardHandlerType.TRICK, requires_target=True
    )
    registry.register(
        CardName.NANMAN, engine._use_nanman,
        CardHandlerType.TRICK, requires_target=False, target_count=0
    )
    registry.register(
        CardName.WANJIAN, engine._use_wanjian,
        CardHandlerType.TRICK, requires_target=False, target_count=0
    )
    registry.register(
        CardName.WUZHONG, engine._use_wuzhong,
        CardHandlerType.TRICK, requires_target=False
    )
    registry.register(
        CardName.GUOHE, engine._use_guohe,
        CardHandlerType.TRICK, requires_target=True
    )
    registry.register(
        CardName.SHUNSHOU, engine._use_shunshou,
        CardHandlerType.TRICK, requires_target=True
    )
    registry.register(
        CardName.TAOYUAN, engine._use_taoyuan,
        CardHandlerType.TRICK, requires_target=False, target_count=0
    )

    # 延时锦囊
    registry.register(
        CardName.LEBUSISHU, engine._use_lebusishu,
        CardHandlerType.DELAY_TRICK, requires_target=True
    )
    registry.register(
        CardName.BINGLIANG, engine._use_bingliang,
        CardHandlerType.DELAY_TRICK, requires_target=True
    )
    registry.register(
        CardName.SHANDIAN, engine._use_shandian,
        CardHandlerType.DELAY_TRICK, requires_target=False
    )

    # 军争锦囊
    registry.register(
        CardName.HUOGONG, engine._use_huogong,
        CardHandlerType.TRICK, requires_target=True
    )


# 全局单例（可选，用于跨模块共享）
_global_registry: Optional[CardHandlerRegistry] = None


def get_global_registry() -> CardHandlerRegistry:
    """获取全局卡牌处理器注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = CardHandlerRegistry()
    return _global_registry
