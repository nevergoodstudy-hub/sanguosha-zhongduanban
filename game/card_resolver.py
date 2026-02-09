"""卡牌效果解析器 (Phase 2.5 — 引擎分解)

从 engine.py 提取的所有 _use_xxx 卡牌效果方法:
- 锦囊牌: 南蛮入侵/万箭齐发/无中生有/过河拆桥/顺手牵羊/借刀杀人/
           桃园结义/乐不思蜀/兵粮寸断/闪电/火攻/铁索连环
- 基本牌: 桃/酒
- 卡牌操作: 选牌弃置/选牌获取

与现有 effect_registry (M1-T02) 协调:
effect_registry 中的 CardEffect.resolve() 仍调用 engine._use_xxx()
→ engine._use_xxx() 委托给 CardResolver 方法。

所有方法依赖 GameContext 协议。
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


class CardResolver:
    """卡牌效果解析器 — 处理所有卡牌使用效果。"""

    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    # ==================== 基本牌 ====================

    def use_tao(self, player: Player, card: Card) -> bool:
        """使用桃"""
        ctx = self.ctx
        if player.hp >= player.max_hp:
            ctx.log_event("error", _t("resolver.hp_full"))
            player.draw_cards([card])
            return False

        healed = player.heal(1)
        ctx.log_event("use_card",
                      _t("resolver.use_tao", name=player.name, healed=healed),
                      source=player, card=card)
        ctx.deck.discard([card])
        return True

    def use_jiu(self, player: Player, card: Card) -> bool:
        """使用酒"""
        ctx = self.ctx

        # 濒死时使用酒回复体力
        if player.is_dying:
            player.heal(1)
            ctx.log_event("use_card",
                          _t("resolver.jiu_heal", name=player.name),
                          source=player, card=card)
            ctx.deck.discard([card])
            return True

        # 出牌阶段使用酒（本回合限一次）
        if player.alcohol_used:
            ctx.log_event("error", _t("resolver.jiu_already_used", name=player.name))
            player.draw_cards([card])
            return False

        if player.use_alcohol():
            ctx.log_event("use_card",
                          _t("resolver.use_jiu", name=player.name),
                          source=player, card=card)
            ctx.deck.discard([card])
            return True

        player.draw_cards([card])
        return False

    # ==================== AOE 锦囊 ====================

    def use_nanman(self, player: Player, card: Card) -> bool:
        """使用南蛮入侵"""
        ctx = self.ctx
        ctx.log_event("use_card", _t("resolver.use_nanman", name=player.name),
                      source=player, card=card)

        for target in ctx.get_other_players(player):
            if ctx._request_wuxie(card, player, target):
                ctx.log_event("effect",
                              _t("resolver.nullified_for", card=_t("card.nanman"), name=target.name))
                continue

            # 藤甲免疫
            if ctx.equipment_sys.is_immune_to_normal_aoe(target):
                ctx.log_event("equipment",
                              _t("resolver.tengjia_immune", name=target.name, card=_t("card.nanman")))
                continue

            sha_count = ctx.combat.request_sha(target, 1)
            if sha_count < 1:
                ctx.log_event("effect", _t("resolver.failed_sha", name=target.name))
                ctx.deal_damage(player, target, 1)
            else:
                ctx.log_event("effect",
                              _t("resolver.played_sha", name=target.name))

        ctx.deck.discard([card])
        return True

    def use_wanjian(self, player: Player, card: Card) -> bool:
        """使用万箭齐发"""
        ctx = self.ctx
        ctx.log_event("use_card", _t("resolver.use_wanjian", name=player.name),
                      source=player, card=card)

        for target in ctx.get_other_players(player):
            if ctx._request_wuxie(card, player, target):
                ctx.log_event("effect",
                              _t("resolver.nullified_for", card=_t("card.wanjian"), name=target.name))
                continue

            # 藤甲免疫
            if ctx.equipment_sys.is_immune_to_normal_aoe(target):
                ctx.log_event("equipment",
                              _t("resolver.tengjia_immune", name=target.name, card=_t("card.wanjian")))
                continue

            shan_count = ctx.combat.request_shan(target, 1)
            if shan_count < 1:
                ctx.log_event("effect", _t("resolver.failed_shan", name=target.name))
                ctx.deal_damage(player, target, 1)
            else:
                ctx.log_event("effect",
                              _t("resolver.played_shan", name=target.name))

        ctx.deck.discard([card])
        return True

    def use_taoyuan(self, player: Player, card: Card) -> bool:
        """使用桃园结义"""
        ctx = self.ctx
        ctx.log_event("use_card", _t("resolver.use_taoyuan", name=player.name),
                      source=player, card=card)

        start_index = ctx.players.index(player)
        for i in range(len(ctx.players)):
            current_index = (start_index + i) % len(ctx.players)
            p = ctx.players[current_index]
            if not p.is_alive:
                continue

            if ctx._request_wuxie(card, player, p):
                ctx.log_event("effect",
                              _t("resolver.nullified_for", card=_t("card.taoyuan"), name=p.name))
                continue

            if p.hp < p.max_hp:
                p.heal(1)
                ctx.log_event("effect", _t("resolver.heal_1", name=p.name))

        ctx.deck.discard([card])
        return True

    # ==================== 单目标锦囊 ====================

    def use_wuzhong(self, player: Player, card: Card) -> bool:
        """使用无中生有"""
        ctx = self.ctx
        ctx.log_event("use_card", _t("resolver.use_wuzhong", name=player.name),
                      source=player, card=card)

        if ctx._request_wuxie(card, player, player):
            ctx.log_event("effect", _t("resolver.nullified", card=_t("card.wuzhong")))
            ctx.deck.discard([card])
            return True

        cards = ctx.deck.draw(2)
        if cards:
            player.draw_cards(cards)
            ctx.log_event("effect", _t("resolver.drew_cards", name=player.name, count=len(cards)))
        else:
            ctx.log_event("error", _t("resolver.deck_empty"))

        ctx.deck.discard([card])
        return True

    def use_guohe(self, player: Player, card: Card,
                  targets: list[Player]) -> bool:
        """使用过河拆桥"""
        ctx = self.ctx
        if not targets:
            ctx.deck.discard([card])
            return False

        target = targets[0]
        if not target.has_any_card():
            ctx.log_event("error", _t("resolver.no_cards_dismantle", name=target.name))
            player.draw_cards([card])
            return False

        ctx.log_event("use_card",
                      _t("resolver.use_guohe", player=player.name, target=target.name),
                      source=player, target=target, card=card)

        if ctx._request_wuxie(card, player, target):
            ctx.log_event("effect", _t("resolver.nullified", card=_t("card.guohe")))
            ctx.deck.discard([card])
            return True

        discarded_card = self.choose_and_discard_card(player, target)
        if discarded_card:
            ctx.log_event("effect",
                          _t("resolver.card_discarded", name=target.name, card=discarded_card.display_name))

        ctx.deck.discard([card])
        return True

    def use_shunshou(self, player: Player, card: Card,
                     targets: list[Player]) -> bool:
        """使用顺手牵羊"""
        ctx = self.ctx
        if not targets:
            ctx.deck.discard([card])
            return False

        target = targets[0]

        if ctx.calculate_distance(player, target) > 1:
            ctx.log_event("error",
                          _t("resolver.shunshou_too_far", name=target.name))
            player.draw_cards([card])
            return False

        if not target.has_any_card():
            ctx.log_event("error", _t("resolver.no_cards_steal", name=target.name))
            player.draw_cards([card])
            return False

        ctx.log_event("use_card",
                      _t("resolver.use_shunshou", player=player.name, target=target.name),
                      source=player, target=target, card=card)

        if ctx._request_wuxie(card, player, target):
            ctx.log_event("effect", _t("resolver.nullified", card=_t("card.shunshou")))
            ctx.deck.discard([card])
            return True

        stolen_card = self.choose_and_steal_card(player, target)
        if stolen_card:
            ctx.log_event("effect",
                          _t("resolver.card_stolen", player=player.name, target=target.name))

        ctx.deck.discard([card])
        return True

    def use_jiedao(self, player: Player, card: Card,
                   targets: list[Player]) -> bool:
        """使用借刀杀人"""
        ctx = self.ctx
        if not targets or len(targets) < 2:
            ctx.deck.discard([card])
            return False

        wielder = targets[0]
        sha_target = targets[1]

        if not wielder.equipment.weapon:
            ctx.log_event("error", _t("resolver.no_weapon", name=wielder.name))
            player.draw_cards([card])
            return False

        if not ctx.is_in_attack_range(wielder, sha_target):
            ctx.log_event("error",
                          _t("resolver.jiedao_out_of_range", target=sha_target.name, wielder=wielder.name))
            player.draw_cards([card])
            return False

        ctx.log_event("use_card",
                      _t("resolver.use_jiedao", player=player.name, wielder=wielder.name, target=sha_target.name),
                      source=player, target=wielder, card=card)

        if ctx._request_wuxie(card, player, wielder):
            ctx.log_event("effect", _t("resolver.nullified", card=_t("card.jiedao")))
            ctx.deck.discard([card])
            return True

        sha_count = ctx.combat.request_sha(wielder, 1)
        if sha_count >= 1:
            ctx.log_event("effect", _t("resolver.played_sha", name=wielder.name))
            shan_count = ctx.combat.request_shan(sha_target, 1)
            if shan_count >= 1:
                ctx.log_event("dodge",
                              _t("combat.dodge_success", name=sha_target.name))
            else:
                ctx.deal_damage(wielder, sha_target, 1)
        else:
            weapon = wielder.equipment.weapon
            if weapon:
                wielder.equipment.unequip(EquipmentSlot.WEAPON)
                player.draw_cards([weapon])
                ctx.log_event("effect",
                              _t("resolver.jiedao_take_weapon", wielder=wielder.name, player=player.name, weapon=weapon.name))

        ctx.deck.discard([card])
        return True

    def use_huogong(self, player: Player, card: Card,
                    targets: list[Player]) -> bool:
        """使用火攻"""
        ctx = self.ctx
        if not targets:
            ctx.deck.discard([card])
            return False

        target = targets[0]
        if not target.hand:
            ctx.log_event("error", _t("resolver.huogong_no_hand", name=target.name))
            ctx.deck.discard([card])
            return False

        ctx.log_event("use_card",
                      _t("resolver.use_huogong", player=player.name, target=target.name),
                      source=player, target=target, card=card)

        if ctx._request_wuxie(card, player, target):
            ctx.log_event("effect", _t("resolver.nullified", card=_t("card.huogong")))
            ctx.deck.discard([card])
            return True

        shown_card = ctx.request_handler.choose_card_to_show(target)
        if not shown_card:
            ctx.deck.discard([card])
            return True

        ctx.log_event("effect",
                      _t("resolver.shown_card", name=target.name, card=shown_card.display_name))

        shown_suit = shown_card.suit
        matching = [c for c in player.hand if c.suit == shown_suit]

        discard_card = None
        if matching:
            discard_card = ctx.request_handler.choose_card_to_discard_for_huogong(
                player, shown_suit)

        if discard_card:
            player.remove_card(discard_card)
            ctx.deck.discard([discard_card])
            ctx.log_event("effect",
                          _t("resolver.discard_for_huogong", name=player.name, card=discard_card.display_name))
            ctx.deal_damage(player, target, 1, damage_type="fire")
        else:
            ctx.log_event("effect",
                          _t("resolver.huogong_no_discard", name=player.name))

        ctx.deck.discard([card])
        return True

    # ==================== 延时锦囊 (使用时) ====================

    def use_lebusishu(self, player: Player, card: Card,
                      targets: list[Player]) -> bool:
        """使用乐不思蜀"""
        ctx = self.ctx
        if not targets:
            player.draw_cards([card])
            return False

        target = targets[0]
        if target == player:
            ctx.log_event("error", _t("resolver.delay_self", card=_t("card.lebusishu")))
            player.draw_cards([card])
            return False

        for c in target.judge_area:
            if c.name == CardName.LEBUSISHU:
                ctx.log_event("error",
                              _t("resolver.delay_exists", name=target.name, card=_t("card.lebusishu")))
                player.draw_cards([card])
                return False

        ctx.log_event("use_card",
                      _t("resolver.use_lebusishu", player=player.name, target=target.name),
                      source=player, target=target, card=card)
        target.judge_area.insert(0, card)
        ctx.log_event("effect",
                      _t("resolver.delay_placed", card=_t("card.lebusishu"), name=target.name))
        return True

    def use_bingliang(self, player: Player, card: Card,
                      targets: list[Player]) -> bool:
        """使用兵粮寸断"""
        ctx = self.ctx
        if not targets:
            player.draw_cards([card])
            return False

        target = targets[0]
        if target == player:
            ctx.log_event("error", _t("resolver.delay_self", card=_t("card.bingliang")))
            player.draw_cards([card])
            return False

        distance = ctx.calculate_distance(player, target)
        if distance > 1:
            ctx.log_event("error",
                          _t("resolver.bingliang_too_far", name=target.name, distance=distance))
            player.draw_cards([card])
            return False

        for c in target.judge_area:
            if c.name == CardName.BINGLIANG:
                ctx.log_event("error",
                              _t("resolver.delay_exists", name=target.name, card=_t("card.bingliang")))
                player.draw_cards([card])
                return False

        ctx.log_event("use_card",
                      _t("resolver.use_bingliang", player=player.name, target=target.name),
                      source=player, target=target, card=card)
        target.judge_area.insert(0, card)
        ctx.log_event("effect",
                      _t("resolver.delay_placed", card=_t("card.bingliang"), name=target.name))
        return True

    def use_shandian(self, player: Player, card: Card,
                     targets: list[Player] = None) -> bool:
        """使用闪电"""
        ctx = self.ctx
        for c in player.judge_area:
            if c.name == CardName.SHANDIAN:
                ctx.log_event("error", _t("resolver.delay_exists", name=player.name, card=_t("card.shandian")))
                player.draw_cards([card])
                return False

        ctx.log_event("use_card", _t("resolver.use_shandian", name=player.name),
                      source=player, card=card)
        player.judge_area.insert(0, card)
        ctx.log_event("effect",
                      _t("resolver.delay_placed", card=_t("card.shandian"), name=player.name))
        return True

    def use_tiesuo(self, player: Player, card: Card,
                   targets: list[Player] | None = None) -> bool:
        """使用铁索连环"""
        ctx = self.ctx
        if targets is None:
            targets = []

        # 无目标 → 重铸
        if not targets:
            ctx.log_event("use_card",
                          _t("resolver.tiesuo_recast", name=player.name),
                          source=player, card=card)
            ctx.deck.discard([card])
            new_cards = ctx.deck.draw(1)
            player.draw_cards(new_cards)
            if new_cards:
                ctx.log_event("effect", _t("resolver.drew_cards", name=player.name, count=1))
            return True

        target_names = "、".join(t.name for t in targets[:2])
        ctx.log_event("use_card",
                      _t("resolver.use_tiesuo", player=player.name, targets=target_names),
                      source=player, card=card)

        for target in targets[:2]:
            target.toggle_chain()
            status = _t("resolver.chain_on") if target.is_chained else _t("resolver.chain_off")
            ctx.log_event("effect",
                          _t("resolver.chain_status", name=target.name, status=status, chained=target.is_chained))

        ctx.deck.discard([card])
        return True

    # ==================== 卡牌操作 ====================

    def choose_and_discard_card(self, player: Player,
                                target: Player) -> Card | None:
        """选择并弃置目标的一张牌"""
        ctx = self.ctx
        all_cards = target.get_all_cards()
        if not all_cards:
            return None

        card = ctx.request_handler.choose_card_from_player(player, target)
        if card:
            if card in target.hand:
                target.remove_card(card)
            else:
                ctx.equipment_sys.remove(target, card)
            ctx.deck.discard([card])
        return card

    def choose_and_steal_card(self, player: Player,
                              target: Player) -> Card | None:
        """选择并获得目标的一张牌"""
        ctx = self.ctx
        all_cards = target.get_all_cards()
        if not all_cards:
            return None

        card = ctx.request_handler.choose_card_from_player(player, target)
        if card:
            if card in target.hand:
                target.remove_card(card)
            else:
                ctx.equipment_sys.remove(target, card)
            player.draw_cards([card])
        return card
