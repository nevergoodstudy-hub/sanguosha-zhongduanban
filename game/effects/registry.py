# -*- coding: utf-8 -*-
"""
卡牌效果注册表（M1-T02 + M2-T04）
"""

from __future__ import annotations
import logging
from typing import Dict, Optional, TYPE_CHECKING

from .base import CardEffect

if TYPE_CHECKING:
    from ..engine import GameEngine
    from ..player import Player
    from ..card import Card

logger = logging.getLogger(__name__)


class CardEffectRegistry:
    """
    卡牌效果注册表

    按卡牌名称映射到 CardEffect 实例，
    engine.use_card() 通过此注册表路由效果执行。

    M2-T04: 支持从 data/card_effects.json 加载数据驱动效果。
    手写 Effect 优先，数据驱动补充未注册的卡牌。
    """

    def __init__(self):
        self._effects: Dict[str, CardEffect] = {}
        self._data_driven_count: int = 0

    def register(self, card_name: str, effect: CardEffect) -> None:
        """注册卡牌效果"""
        self._effects[card_name] = effect

    def get(self, card_name: str) -> Optional[CardEffect]:
        """获取卡牌效果处理器"""
        return self._effects.get(card_name)

    def has(self, card_name: str) -> bool:
        """检查是否有对应的效果处理器"""
        return card_name in self._effects

    def load_data_driven(self) -> int:
        """
        M2-T04: 从 data/card_effects.json 加载数据驱动效果。
        仅为尚未注册的卡牌创建 DataDrivenCardEffect。

        Returns:
            新增的数据驱动效果数量
        """
        from .data_driven import DataDrivenCardEffect, load_card_effects_config

        configs = load_card_effects_config()
        count = 0
        for card_name, config in configs.items():
            if card_name not in self._effects:
                self._effects[card_name] = DataDrivenCardEffect(card_name, config)
                count += 1

        self._data_driven_count = count
        if count:
            logger.info("Loaded %d data-driven card effects", count)
        return count


def create_default_registry() -> CardEffectRegistry:
    """
    创建并注册所有默认卡牌效果

    Returns:
        已注册所有效果的注册表
    """
    from ..card import CardName
    from .basic import ShaEffect, TaoEffect, JiuEffect
    from .trick import (
        JuedouEffect, NanmanEffect, WanjianEffect,
        WuzhongEffect, GuoheEffect, ShunshouEffect,
        TaoyuanEffect, LebusishuEffect, BingliangEffect,
        ShandianEffect, HuogongEffect, TiesuoEffect,
    )

    registry = CardEffectRegistry()

    # 基本牌
    registry.register(CardName.SHA, ShaEffect())
    registry.register(CardName.TAO, TaoEffect())
    # 酒通过 subtype 匹配，不通过 name

    # 锦囊牌
    registry.register(CardName.JUEDOU, JuedouEffect())
    registry.register(CardName.NANMAN, NanmanEffect())
    registry.register(CardName.WANJIAN, WanjianEffect())
    registry.register(CardName.WUZHONG, WuzhongEffect())
    registry.register(CardName.GUOHE, GuoheEffect())
    registry.register(CardName.SHUNSHOU, ShunshouEffect())
    registry.register(CardName.TAOYUAN, TaoyuanEffect())
    registry.register(CardName.LEBUSISHU, LebusishuEffect())
    registry.register(CardName.BINGLIANG, BingliangEffect())
    registry.register(CardName.SHANDIAN, ShandianEffect())
    registry.register(CardName.HUOGONG, HuogongEffect())

    # M2-T04: 加载数据驱动效果（补充未手写的卡牌）
    registry.load_data_driven()

    return registry
