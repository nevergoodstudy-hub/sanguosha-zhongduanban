"""基本牌效果处理器（M1-T02）
杀、桃、酒
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from i18n import t as _t

from .base import CardEffect

if TYPE_CHECKING:
    pass


class ShaEffect(CardEffect):
    """杀的效果"""

    @property
    def needs_target(self) -> bool:
        return True

    def can_use(self, engine, player, card, targets):
        if not targets:
            return False, _t("effect.need_target")
        if not player.can_use_sha():
            return False, _t("effect.sha_used")
        if not engine.is_in_attack_range(player, targets[0]):
            return False, _t("effect.out_of_range")
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine.combat.use_sha(player, card, targets)


class TaoEffect(CardEffect):
    """桃的效果"""

    def can_use(self, engine, player, card, targets):
        if player.hp >= player.max_hp:
            return False, _t("error.hp_full")
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine.card_resolver.use_tao(player, card)


class JiuEffect(CardEffect):
    """酒的效果"""

    def can_use(self, engine, player, card, targets):
        if player.is_dying:
            return True, ""
        if player.alcohol_used:
            return False, _t("effect.jiu_used")
        return True, ""

    def resolve(self, engine, player, card, targets):
        return engine.card_resolver.use_jiu(player, card)
