# -*- coding: utf-8 -*-
"""
基本牌效果处理器（M1-T02）
杀、桃、酒
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .base import CardEffect

if TYPE_CHECKING:
    from ..engine import GameEngine
    from ..player import Player
    from ..card import Card


class ShaEffect(CardEffect):
    """杀的效果"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        if not player.can_use_sha():
            return False, "本回合已经使用过杀了"
        if not engine.is_in_attack_range(player, targets[0]):
            return False, "目标不在攻击范围内"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_sha(player, card, targets)


class TaoEffect(CardEffect):
    """桃的效果"""

    def can_use(self, engine, player, card, targets):
        if player.hp >= player.max_hp:
            return False, "体力已满"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_tao(player, card)


class JiuEffect(CardEffect):
    """酒的效果"""

    def can_use(self, engine, player, card, targets):
        if player.is_dying:
            return True, ""
        if player.alcohol_used:
            return False, "本回合已经使用过酒了"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_jiu(player, card)
