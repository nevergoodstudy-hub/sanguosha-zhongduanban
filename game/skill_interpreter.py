"""技能 DSL 解释器

M2-T02: 读取技能 DSL 并执行。
与 SkillSystem 的 Python handler 共存（混合模式），
DSL 优先、Python fallback。
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

from i18n import t as _t

from .skill_dsl import SkillDsl

if TYPE_CHECKING:
    from .card import Card
    from .engine import GameEngine
    from .player import Player

logger = logging.getLogger(__name__)


class DslContext:
    """DSL 执行上下文

    在一次技能执行过程中携带临时状态。
    """

    def __init__(
        self,
        engine: GameEngine,
        player: Player,
        skill_name: str,
        targets: list[Player] | None = None,
        cards: list[Card] | None = None,
        source: Player | None = None,
        damage_card: Card | None = None,
        **extra: Any,
    ):
        self.engine = engine
        self.player = player
        self.skill_name = skill_name
        self.targets = targets or []
        self.target = targets[0] if targets else None
        self.cards = cards or []
        self.source = source
        self.damage_card = damage_card
        self.extra = extra

        # 运行时累加器（如仁德的已送牌数）
        self.counters: dict[str, int] = {}


class SkillInterpreter:
    """技能 DSL 解释器

    职责：
    - 解析 SkillDsl 数据
    - 检查条件 (condition)
    - 执行代价 (cost)
    - 按序执行步骤 (steps)
    """

    def __init__(self, engine: GameEngine):
        self.engine = engine

    # ==================== 公开 API ====================

    def can_execute(self, dsl: SkillDsl, player: Player, **kwargs) -> bool:
        """检查 DSL 技能是否可执行"""
        ctx = DslContext(self.engine, player, "", **kwargs)

        # 检查每回合限制
        if dsl.limit > 0:
            skill_id = kwargs.get('skill_id', '')
            used = player.skill_used.get(skill_id, 0)
            if used >= dsl.limit:
                return False

        # 检查条件
        for cond in dsl.condition:
            if not self._eval_condition(cond, ctx):
                return False

        # 检查代价可支付
        for cost in dsl.cost:
            if not self._can_pay_cost(cost, ctx):
                return False

        return True

    def execute(
        self,
        dsl: SkillDsl,
        player: Player,
        skill_name: str,
        targets: list[Player] | None = None,
        cards: list[Card] | None = None,
        **kwargs,
    ) -> bool:
        """执行 DSL 技能

        Args:
            dsl: 技能 DSL 定义
            player: 使用技能的玩家
            skill_name: 技能中文名（用于日志）
            targets: 目标列表
            cards: 选择的卡牌
            **kwargs: 额外参数 (source, damage_card, ...)

        Returns:
            是否成功执行
        """
        ctx = DslContext(
            self.engine, player, skill_name,
            targets=targets, cards=cards, **kwargs,
        )

        # 1. 检查条件
        for cond in dsl.condition:
            if not self._eval_condition(cond, ctx):
                return False

        # 2. 支付代价
        for cost in dsl.cost:
            if not self._pay_cost(cost, ctx):
                return False

        # 3. 执行步骤
        for step in dsl.steps:
            self._exec_step(step, ctx)

        return True

    # ==================== 条件检查 ====================

    def _eval_condition(self, cond: dict[str, Any], ctx: DslContext) -> bool:
        """评估单个条件"""
        check = cond.get("check", "")

        if check == "has_hand_cards":
            min_count = cond.get("min", 1)
            return len(ctx.player.hand) >= min_count

        if check == "hp_below_max":
            return ctx.player.hp < ctx.player.max_hp

        if check == "hp_above":
            return ctx.player.hp >= cond.get("value", 1)

        if check == "target_has_cards":
            return ctx.target is not None and ctx.target.has_any_card()

        if check == "no_sha_used":
            return ctx.player.sha_count == 0

        if check == "distance_le":
            if not ctx.target:
                return False
            dist = ctx.engine.calculate_distance(ctx.player, ctx.target)
            return dist <= cond.get("value", 1)

        if check == "target_hand_ge_hp":
            return ctx.target is not None and ctx.target.hand_count >= ctx.player.hp

        if check == "target_hand_le_range":
            return ctx.target is not None and ctx.target.hand_count <= ctx.player.equipment.attack_range

        if check == "source_hand_ge":
            return ctx.source is not None and ctx.source.hand_count >= cond.get("value", 1)

        logger.warning("Unknown DSL condition: %s", check)
        return True  # 未知条件默认通过

    # ==================== 代价 ====================

    def _can_pay_cost(self, cost: dict[str, Any], ctx: DslContext) -> bool:
        """检查代价是否可支付"""
        if "discard" in cost:
            info = cost["discard"]
            count = info.get("count", 1)
            return len(ctx.player.hand) >= count

        if "lose_hp" in cost:
            amount = cost["lose_hp"]
            return ctx.player.hp > amount  # 必须存活

        return True

    def _pay_cost(self, cost: dict[str, Any], ctx: DslContext) -> bool:
        """支付代价"""
        if "discard" in cost:
            info = cost["discard"]
            count = info.get("count", 1)
            if ctx.cards and len(ctx.cards) >= count:
                # 使用玩家选择的牌
                to_discard = ctx.cards[:count]
            else:
                # 自动选择
                to_discard = ctx.player.hand[:count]
            for c in to_discard:
                if c in ctx.player.hand:
                    ctx.player.remove_card(c)
            ctx.engine.deck.discard(to_discard)
            return True

        if "lose_hp" in cost:
            amount = cost["lose_hp"]
            ctx.player.hp -= amount
            return True

        return True

    # ==================== 步骤执行 ====================

    def _exec_step(self, step: dict[str, Any], ctx: DslContext) -> None:
        """执行单个步骤"""
        # ---------- draw ----------
        if "draw" in step:
            count = step["draw"]
            cards = ctx.engine.deck.draw(count)
            target_str = step.get("target", "self")
            recipient = self._resolve_player(target_str, ctx)
            recipient.draw_cards(cards)

        # ---------- heal ----------
        elif "heal" in step:
            info = step["heal"]
            if isinstance(info, int):
                ctx.player.heal(info)
            else:
                amount = info.get("amount", 1)
                target_str = info.get("target", "self")
                recipient = self._resolve_player(target_str, ctx)
                recipient.heal(amount)

        # ---------- damage ----------
        elif "damage" in step:
            info = step["damage"]
            amount = info.get("amount", 1)
            target_str = info.get("target", "source")
            damage_type = info.get("type", "normal")
            victim = self._resolve_player(target_str, ctx)
            if victim and victim.is_alive:
                ctx.engine.deal_damage(ctx.player, victim, amount, damage_type)

        # ---------- lose_hp ----------
        elif "lose_hp" in step:
            amount = step["lose_hp"]
            ctx.player.hp -= amount

        # ---------- flip ----------
        elif "flip" in step:
            ctx.player.toggle_flip()

        # ---------- get_card ----------
        elif "get_card" in step:
            info = step["get_card"]
            source_str = info.get("from", "discard_pile")

            if source_str == "damage_card":
                card = ctx.damage_card
                if card and card in ctx.engine.deck.discard_pile:
                    ctx.engine.deck.discard_pile.remove(card)
                    ctx.player.draw_cards([card])

            elif source_str == "source":
                source_player = ctx.source
                if source_player and source_player.has_any_card():
                    all_cards = source_player.get_all_cards()
                    card = random.choice(all_cards)
                    if card in source_player.hand:
                        source_player.remove_card(card)
                    else:
                        source_player.equipment.unequip_card(card)
                    ctx.player.draw_cards([card])

        # ---------- discard ----------
        elif "discard" in step:
            info = step["discard"]
            count = info.get("count", 1)
            source_str = info.get("from", "hand")
            target_str = info.get("player", "self")
            target_player = self._resolve_player(target_str, ctx)

            if source_str == "hand" and target_player:
                to_discard = target_player.hand[:count]
                for c in to_discard:
                    target_player.remove_card(c)
                ctx.engine.deck.discard(to_discard)

        # ---------- transfer ----------
        elif "transfer" in step:
            info = step["transfer"]
            if ctx.cards and ctx.target:
                transferred = []
                for card in ctx.cards:
                    if card in ctx.player.hand:
                        ctx.player.remove_card(card)
                        transferred.append(card)
                if transferred:
                    ctx.target.draw_cards(transferred)
                    # 更新计数器
                    key = "transfer_count"
                    ctx.counters[key] = ctx.counters.get(key, 0) + len(transferred)

        # ---------- judge ----------
        elif "judge" in step:
            info = step["judge"]
            judge_cards = ctx.engine.deck.draw(1)
            if judge_cards:
                judge_card = judge_cards[0]
                ctx.engine.log_event(
                    "judge",
                    _t("judge.result", card=judge_card.display_name)
                )
                ctx.engine.deck.discard([judge_card])

                # 评估判定条件
                success_cond = info.get("success_if", {})
                is_success = self._eval_judge(judge_card, success_cond)

                if is_success:
                    for s in info.get("success", []):
                        self._exec_step(s, ctx)
                else:
                    for s in info.get("fail", []):
                        self._exec_step(s, ctx)

        # ---------- skip_phase ----------
        elif "skip_phase" in step:
            phase = step["skip_phase"]
            if phase == "discard":
                ctx.player.skip_discard = True

        # ---------- if ----------
        elif "if" in step:
            cond = step["if"]
            if self._eval_condition(cond, ctx):
                for s in step.get("then", []):
                    self._exec_step(s, ctx)
            else:
                for s in step.get("else", []):
                    self._exec_step(s, ctx)

        # ---------- log ----------
        elif "log" in step:
            msg = step["log"]
            # 简单模板替换
            msg = msg.replace("{player}", ctx.player.name)
            if ctx.target:
                msg = msg.replace("{target}", ctx.target.name)
            if ctx.source:
                msg = msg.replace("{source}", ctx.source.name)
            msg = msg.replace("{skill}", ctx.skill_name)
            ctx.engine.log_event("skill", msg)

    # ==================== 辅助 ====================

    def _resolve_player(self, ref: str, ctx: DslContext) -> Player:
        """解析玩家引用"""
        if ref == "self":
            return ctx.player
        if ref == "target":
            return ctx.target or ctx.player
        if ref == "source":
            return ctx.source or ctx.player
        return ctx.player

    def _eval_judge(self, card: Card, cond: dict[str, Any]) -> bool:
        """评估判定结果"""
        from .card import CardSuit

        if not cond:
            return True

        suit = cond.get("suit")
        not_suit = cond.get("not_suit")
        color = cond.get("color")

        if suit:
            suit_enum = CardSuit(suit)
            return card.suit == suit_enum

        if not_suit:
            suit_enum = CardSuit(not_suit)
            return card.suit != suit_enum

        if color:
            if color == "red":
                return card.is_red
            elif color == "black":
                return not card.is_red

        return True
