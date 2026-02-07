# -*- coding: utf-8 -*-
"""
卡牌效果处理器模块（M1-T02）

将卡牌效果逻辑从 engine.py 中解耦，
每种卡牌拥有独立的 Effect 类。
"""

from .base import CardEffect
from .registry import CardEffectRegistry
from .data_driven import DataDrivenCardEffect

__all__ = ['CardEffect', 'CardEffectRegistry', 'DataDrivenCardEffect']
