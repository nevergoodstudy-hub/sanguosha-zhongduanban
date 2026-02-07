# -*- coding: utf-8 -*-
"""
锦囊牌效果处理器（M1-T02）
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .base import CardEffect

if TYPE_CHECKING:
    from ..engine import GameEngine
    from ..player import Player
    from ..card import Card


class JuedouEffect(CardEffect):
    """决斗"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_juedou(player, card, targets)


class NanmanEffect(CardEffect):
    """南蛮入侵"""

    def can_use(self, engine, player, card, targets):
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_nanman(player, card)


class WanjianEffect(CardEffect):
    """万箭齐发"""

    def can_use(self, engine, player, card, targets):
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_wanjian(player, card)


class WuzhongEffect(CardEffect):
    """无中生有"""

    def can_use(self, engine, player, card, targets):
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_wuzhong(player, card)


class GuoheEffect(CardEffect):
    """过河拆桥"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_guohe(player, card, targets)


class ShunshouEffect(CardEffect):
    """顺手牵羊"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_shunshou(player, card, targets)


class TaoyuanEffect(CardEffect):
    """桃园结义"""

    def can_use(self, engine, player, card, targets):
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_taoyuan(player, card)


class LebusishuEffect(CardEffect):
    """乐不思蜀"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_lebusishu(player, card, targets)


class BingliangEffect(CardEffect):
    """兵粮寸断"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_bingliang(player, card, targets)


class ShandianEffect(CardEffect):
    """闪电"""

    def can_use(self, engine, player, card, targets):
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_shandian(player, card, targets)


class HuogongEffect(CardEffect):
    """火攻"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, "必须指定目标"
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_huogong(player, card, targets)


class TiesuoEffect(CardEffect):
    """铁索连环"""

    def can_use(self, engine, player, card, targets):
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine._use_tiesuo(player, card, targets)
