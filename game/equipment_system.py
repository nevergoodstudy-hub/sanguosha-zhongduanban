"""装备子系统 (Phase 2.3 — 引擎分解)

从 engine.py 提取的装备相关逻辑:
- 装备/卸装流程 (含白银狮子失去装备回复)
- 护甲伤害修正 (藤甲火伤+1, 白银狮子伤害封顶)
- AOE 免疫判定 (藤甲 vs 南蛮入侵/万箭齐发)

所有方法依赖 GameContext 协议而非 GameEngine 具体类。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from i18n import t as _t

from .card import CardName
from .player import EquipmentSlot

if TYPE_CHECKING:
    from .card import Card
    from .context import GameContext
    from .player import Player

logger = logging.getLogger(__name__)


class EquipmentSystem:
    """装备子系统 — 处理装备穿戴/移除和被动装备效果。"""

    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    # ==================== 装备穿戴/移除 ====================

    def equip(self, player: Player, card: Card) -> bool:
        """装备一张装备牌, 替换同槽位旧装备。

        旧装备自动进入弃牌堆。
        """
        ctx = self.ctx
        old_equipment = player.equip_card(card)
        ctx.log_event("equip", _t("equipment.equipped", name=player.name, card=card.name),
                      source=player, card=card)

        if old_equipment:
            ctx.log_event("equip", _t("equipment.replaced", card=old_equipment.name))
            ctx.deck.discard([old_equipment])

        return True

    def remove(self, player: Player, card: Card) -> None:
        """移除玩家装备区的指定装备牌并触发脱装效果。

        白银狮子: 失去此装备时回复 1 点体力。
        """
        ctx = self.ctx
        card_name = card.name

        # 从装备区移除
        for slot in EquipmentSlot:
            if player.equipment.get_card_by_slot(slot) == card:
                player.equipment.unequip(slot)
                break

        # 白银狮子效果
        if (card_name == CardName.BAIYINSHIZI
                and player.is_alive
                and player.hp < player.max_hp):
            player.heal(1)
            ctx.log_event(
                "equipment",
                _t("equipment.baiyinshizi_heal", name=player.name, hp=player.hp, max_hp=player.max_hp),
            )

    # ==================== 护甲伤害修正 ====================

    def modify_damage(self, target: Player, damage: int,
                      damage_type: str) -> int:
        """根据目标护甲修正伤害值。

        - 藤甲: 火焰伤害 +1
        - 白银狮子: 超过 1 的伤害封顶为 1

        返回修正后的伤害值。
        """
        ctx = self.ctx
        armor = target.equipment.armor

        # 藤甲: 火焰伤害 +1
        if damage_type == "fire" and armor and armor.name == CardName.TENGJIA:
            damage += 1
            ctx.log_event(
                "equipment",
                _t("damage.tengjia_fire", name=target.name),
            )

        # 白银狮子: 伤害封顶为 1
        if armor and armor.name == CardName.BAIYINSHIZI and damage > 1:
            original = damage
            damage = 1
            ctx.log_event(
                "equipment",
                _t("damage.baiyinshizi_prevent", name=target.name, prevented=original - 1),
            )

        return damage

    # ==================== AOE 免疫 ====================

    def is_immune_to_normal_aoe(self, target: Player) -> bool:
        """判断目标是否因装备免疫普通 AOE (南蛮入侵/万箭齐发)。

        藤甲使南蛮入侵和万箭齐发无效。
        """
        armor = target.equipment.armor
        if armor and armor.name == CardName.TENGJIA:
            return True
        return False
