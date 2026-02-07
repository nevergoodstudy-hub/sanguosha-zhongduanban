# -*- coding: utf-8 -*-
"""
卡牌效果基类（M1-T02）
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine import GameEngine
    from ..player import Player
    from ..card import Card


class CardEffect(ABC):
    """
    卡牌效果抽象基类

    每种卡牌（杀、桃、决斗等）对应一个 CardEffect 子类，
    通过 CardEffectRegistry 按卡牌名称自动路由。
    """

    @abstractmethod
    def can_use(self, engine: 'GameEngine', player: 'Player',
                card: 'Card', targets: List['Player']) -> tuple[bool, str]:
        """
        检查是否可以使用此卡牌

        Returns:
            (可否使用, 错误原因)
        """
        pass

    @abstractmethod
    def resolve(self, engine: 'GameEngine', player: 'Player',
                card: 'Card', targets: List['Player']) -> bool:
        """
        执行卡牌效果

        Returns:
            是否成功执行
        """
        pass

    @property
    def needs_target(self) -> bool:
        """是否需要指定目标"""
        return False
