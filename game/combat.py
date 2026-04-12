"""战斗子系统 (Phase 2.2 — 引擎分解).

从 engine.py 提取的战斗相关逻辑:
- 杀/闪/决斗 的完整流程
- 无懈可击响应链
- 酒加成、无双、空城等技能交互

所有方法依赖 GameContext 协议而非 GameEngine 具体类。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from i18n import t as _t

from .card import CardName, CardSubtype
from .constants import SkillId
from .events import EventType

if TYPE_CHECKING:
    from .card import Card
    from .context import GameContext
    from .player import Player

logger = logging.getLogger(__name__)


class CombatSystem:
    """战斗子系统 — 处理杀/闪/决斗/无懈可击。."""

    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    def _request_skill_conversion_card(
        self,
        player: Player,
        skill_name: str,
        candidates: list[Card],
    ) -> Card | None:
        """通过统一请求边界选择转换技要使用的牌."""
        if not candidates:
            return None
        return self.ctx.request_handler.request_skill_card(player, skill_name, candidates)

    # ==================== 杀 ====================

    def use_sha(self, player: Player, card: Card, targets: list[Player]) -> bool:
        """使用杀 (支持酒加成、火杀/雷杀属性伤害)。."""
        ctx = self.ctx
        if not targets:
            ctx.deck.discard([card])
            return False

        target = targets[0]

        if not player.can_use_sha():
            ctx.log_event("error", _t("combat.sha_already_used", name=player.name))
            player.draw_cards([card])
            return False

        if not ctx.is_in_attack_range(player, target):
            ctx.log_event("error", _t("combat.target_out_of_range", name=target.name))
            player.draw_cards([card])
            return False

        # 空城
        if target.has_skill(SkillId.KONGCHENG) and target.hand_count == 0:
            ctx.log_event("skill", _t("combat.kongcheng_sha", name=target.name))
            player.draw_cards([card])
            return False

        # 确定伤害类型
        card_name = card.name
        if card.subtype == CardSubtype.FIRE_ATTACK:
            card_name = _t("card.fire_sha")
            damage_type = "fire"
        elif card.subtype == CardSubtype.THUNDER_ATTACK:
            card_name = _t("card.thunder_sha")
            damage_type = "thunder"
        else:
            damage_type = "normal"
            # 朱雀羽扇
            if player.equipment.weapon and player.equipment.weapon.name == CardName.ZHUQUEYUSHAN:
                use_fire = ctx.request_handler.ask_zhuque_convert(player)
                if use_fire:
                    damage_type = "fire"
                    card_name = _t("card.fire_sha")
                    ctx.log_event("equipment", _t("combat.zhuque_convert", name=player.name))

        # 仁王盾 (只对黑色普通杀有效)
        if (
            card.is_black
            and damage_type == "normal"
            and target.equipment.armor
            and target.equipment.armor.name == CardName.RENWANG
        ):
            ctx.log_event("equipment", _t("combat.renwang_block", name=target.name))
            player.use_sha()
            ctx.deck.discard([card])
            return True

        # 藤甲对普通杀无效
        if (
            damage_type == "normal"
            and target.equipment.armor
            and target.equipment.armor.name == CardName.TENGJIA
        ):
            ctx.log_event("equipment", _t("combat.tengjia_block", name=target.name))
            player.use_sha()
            ctx.deck.discard([card])
            return True

        # 酒加成
        base_damage = 1
        is_drunk = player.consume_drunk()
        if is_drunk:
            base_damage += 1
            ctx.log_event("effect", _t("combat.drunk_bonus", name=player.name))

        player.use_sha()
        dist = ctx.calculate_distance(player, target)

        type_icon = {"fire": "🔥", "thunder": "⚡"}.get(damage_type, "⚔")
        ctx.log_event(
            "use_card",
            _t(
                "combat.use_sha",
                icon=type_icon,
                player=player.name,
                target=target.name,
                card=card_name,
                suit=card.suit.symbol,
                number=card.number_str,
                distance=dist,
            ),
            source=player,
            target=target,
            card=card,
        )

        # 无双
        required_shan = 2 if player.has_skill(SkillId.WUSHUANG) else 1
        if required_shan > 1:
            ctx.log_event(
                "skill", _t("combat.wushuang_require", name=player.name, count=required_shan)
            )

        shan_count = self.request_shan(target, required_shan)

        if shan_count >= required_shan:
            ctx.log_event("dodge", _t("combat.dodge_success", name=target.name))
            ctx.event_bus.emit(
                EventType.ATTACK_DODGED,
                source=player,
                target=target,
                card=card,
                required_shan=required_shan,
                played_shan=shan_count,
            )
            # 青龙偃月刀
            if player.equipment.weapon and player.equipment.weapon.name == CardName.QINGLONG:
                self._trigger_qinglong(player, target)
        else:
            ctx.event_bus.emit(
                EventType.ATTACK_HIT,
                source=player,
                target=target,
                card=card,
                damage=base_damage,
            )
            # 古锤刀
            if (
                player.equipment.weapon
                and player.equipment.weapon.name == CardName.GUDINGDAO
                and target.hand_count == 0
            ):
                base_damage += 1
                ctx.log_event(
                    "equipment",
                    _t("combat.gudingdao_bonus", player=player.name, target=target.name),
                )
            ctx.deal_damage(player, target, base_damage, damage_type)

        ctx.deck.discard([card])
        return True

    # ==================== 闪请求 ====================

    def request_shan(self, player: Player, count: int = 1) -> int:
        """请求玩家出闪，返回实际打出的闪数量。."""
        ctx = self.ctx
        shan_played = 0

        for _ in range(count):
            # 八卦阵
            if (
                player.equipment.armor
                and player.equipment.armor.name == CardName.BAGUA
                and self._trigger_bagua(player)
            ):
                shan_played += 1
                continue

            # 龙胆: 杀当闪
            if player.has_skill(SkillId.LONGDAN):
                sha_cards = player.get_cards_by_name(CardName.SHA)
                if sha_cards:
                    card = self._request_skill_conversion_card(player, "longdan_as_shan", sha_cards)
                    if card:
                        player.remove_card(card)
                        ctx.deck.discard([card])
                        ctx.log_event(
                            "skill",
                            _t("combat.longdan_as_shan", name=player.name, card=card.display_name),
                        )
                        shan_played += 1
                        continue

            # 重身: 本轮获得的红色牌可当闪
            if player.has_skill(SkillId.ZHONGSHEN):
                zhongshen_state = player.get_skill_state(SkillId.ZHONGSHEN)
                obtained_ids = set(zhongshen_state.get("round_red_card_ids", set()))
                red_cards = [
                    card for card in player.hand if card.is_red and card.id in obtained_ids
                ]
                if red_cards:
                    card = self._request_skill_conversion_card(
                        player, "zhongshen_as_shan", red_cards
                    )
                    if card:
                        player.remove_card(card)
                        ctx.deck.discard([card])
                        ctx.log_event(
                            "skill",
                            f"{player.name}发动【重身】，将{card.display_name}当【闪】使用",
                        )
                        shan_played += 1
                        continue

            card = ctx.request_handler.request_shan(player)
            if card:
                player.remove_card(card)
                ctx.deck.discard([card])
                shan_played += 1
            else:
                break

        return shan_played

    # ==================== 杀请求 ====================

    def request_sha(self, player: Player, count: int = 1) -> int:
        """请求玩家出杀，返回实际打出的杀数量。."""
        ctx = self.ctx
        sha_played = 0

        for _ in range(count):
            # 武圣: 红色牌当杀
            if player.has_skill(SkillId.WUSHENG):
                red_cards = player.get_red_cards()
                if red_cards:
                    card = self._request_skill_conversion_card(player, "wusheng_as_sha", red_cards)
                    if card:
                        player.remove_card(card)
                        ctx.deck.discard([card])
                        ctx.log_event(
                            "skill",
                            _t("combat.wusheng_as_sha", name=player.name, card=card.display_name),
                        )
                        sha_played += 1
                        continue

            # 龙胆: 闪当杀
            if player.has_skill(SkillId.LONGDAN):
                shan_cards = player.get_cards_by_name(CardName.SHAN)
                if shan_cards:
                    card = self._request_skill_conversion_card(player, "longdan_as_sha", shan_cards)
                    if card:
                        player.remove_card(card)
                        ctx.deck.discard([card])
                        ctx.log_event(
                            "skill",
                            _t("combat.longdan_as_sha", name=player.name, card=card.display_name),
                        )
                        sha_played += 1
                        continue

            card = ctx.request_handler.request_sha(player)
            if card:
                player.remove_card(card)
                ctx.deck.discard([card])
                sha_played += 1
            else:
                break

        return sha_played

    # ==================== 决斗 ====================

    def use_juedou(self, player: Player, card: Card, targets: list[Player]) -> bool:
        """使用决斗。."""
        ctx = self.ctx
        if not targets:
            ctx.deck.discard([card])
            return False

        target = targets[0]

        if target.has_skill(SkillId.KONGCHENG) and target.hand_count == 0:
            ctx.log_event("skill", _t("combat.kongcheng_juedou", name=target.name))
            player.draw_cards([card])
            return False

        ctx.log_event(
            "use_card",
            _t("combat.use_juedou", player=player.name, target=target.name),
            source=player,
            target=target,
            card=card,
        )

        if self.request_wuxie(card, player, target):
            ctx.log_event("effect", _t("combat.juedou_nullified"))
            ctx.deck.discard([card])
            return True

        attacker_required = 2 if player.has_skill(SkillId.WUSHUANG) else 1
        defender_required = 2 if player.has_skill(SkillId.WUSHUANG) else 1

        current_attacker = target
        current_defender = player

        while True:
            required = defender_required if current_attacker == target else attacker_required
            sha_count = self.request_sha(current_attacker, required)

            if sha_count < required:
                ctx.deal_damage(current_defender, current_attacker, 1)
                break

            current_attacker, current_defender = current_defender, current_attacker

        ctx.deck.discard([card])
        return True

    def use_juedou_forced(self, source: Player, target: Player) -> None:
        """强制决斗 (离间等技能, 无需卡牌)。."""
        ctx = self.ctx

        if target.has_skill(SkillId.KONGCHENG) and target.hand_count == 0:
            ctx.log_event("skill", _t("combat.kongcheng_juedou", name=target.name))
            return

        ctx.log_event("effect", _t("combat.forced_juedou", source=source.name, target=target.name))

        attacker_required = 2 if source.has_skill(SkillId.WUSHUANG) else 1
        defender_required = 2 if source.has_skill(SkillId.WUSHUANG) else 1

        current_attacker = target
        current_defender = source

        while True:
            required = defender_required if current_attacker == target else attacker_required
            sha_count = self.request_sha(current_attacker, required)

            if sha_count < required:
                ctx.deal_damage(current_defender, current_attacker, 1)
                break

            current_attacker, current_defender = current_defender, current_attacker

    # ==================== 无懈可击 ====================

    # 无懂可击链最大深度（防止无限循环）
    _WUXIE_MAX_DEPTH: int = 10

    def request_wuxie(
        self,
        trick_card: Card,
        source: Player,
        target: Player | None = None,
        is_delay: bool = False,
    ) -> bool:
        """无懂可击响应链。返回 True 表示锯囊被抵消。.

        规则：所有玩家按座位顺序依次有机会使用无懂可击。
        每次无懂可击打出后，其他玩家可以再使用无懂可击来抵消前一张无懂可击。
        偶数深度 = 抵消原锯囊，奇数深度 = 反抵消（让原锯囊生效）。
        最大深度 {_WUXIE_MAX_DEPTH} 层以防止无限循环。
        """
        ctx = self.ctx

        if trick_card.name == CardName.WUXIE:
            return False

        is_cancelled = False
        depth = 0
        start_index = ctx.players.index(source)

        while depth < self._WUXIE_MAX_DEPTH:
            wuxie_played = False

            for i in range(len(ctx.players)):
                current_index = (start_index + i) % len(ctx.players)
                responder = ctx.players[current_index]

                if not responder.is_alive:
                    continue

                wuxie_cards = responder.get_cards_by_name(CardName.WUXIE)
                if not wuxie_cards:
                    continue

                result = ctx.request_handler.request_wuxie(
                    responder, trick_card, source, target, is_cancelled
                )
                if result:
                    responder.remove_card(result)
                    ctx.deck.discard([result])

                    action_text = (
                        _t("combat.wuxie_cancel")
                        if not is_cancelled
                        else _t("combat.wuxie_activate")
                    )
                    ctx.log_event(
                        "wuxie",
                        _t(
                            "combat.wuxie_played",
                            name=responder.name,
                            action=action_text,
                            card=trick_card.name,
                        ),
                    )
                    is_cancelled = not is_cancelled
                    wuxie_played = True
                    depth += 1
                    break

            if not wuxie_played:
                break

        if depth >= self._WUXIE_MAX_DEPTH:
            logger.warning(
                "Wuxie chain reached max depth (%d), ending chain",
                self._WUXIE_MAX_DEPTH,
            )

        return is_cancelled

    # ==================== 装备触发 (战斗相关) ====================

    def _trigger_bagua(self, player: Player) -> bool:
        """触发八卦阵判定。."""
        ctx = self.ctx
        ctx.log_event("equipment", _t("combat.bagua_try", name=player.name))

        judge_cards = ctx.deck.draw(1)
        if not judge_cards:
            ctx.log_event("error", _t("combat.deck_empty_bagua"))
            return False

        judge_card = judge_cards[0]
        ctx.log_event("judge", _t("combat.judge_result", card=judge_card.display_name))
        ctx.deck.discard([judge_card])

        if judge_card.is_red:
            ctx.log_event("equipment", _t("combat.bagua_success"))
            return True

        ctx.log_event("equipment", _t("combat.bagua_fail"))
        return False

    def _trigger_qinglong(self, player: Player, target: Player) -> None:
        """触发青龙偃月刀效果。."""
        ctx = self.ctx
        sha_cards = player.get_cards_by_name(CardName.SHA)
        if sha_cards:
            ctx.log_event("equipment", _t("combat.qinglong_prompt", name=player.name))
            if player.is_ai and player.id in ctx.ai_bots:
                bot = ctx.ai_bots[player.id]
                if hasattr(bot, "should_use_qinglong") and bot.should_use_qinglong(
                    player, target, ctx
                ):
                    card = sha_cards[0]
                    player.remove_card(card)
                    self.use_sha(player, card, [target])
