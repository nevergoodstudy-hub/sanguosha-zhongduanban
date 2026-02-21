"""判定子系统 (Phase 2.4 — 引擎分解)

从 engine.py 提取的判定阶段逻辑:
- 延时锦囊判定 (乐不思蜀/兵粮寸断/闪电)
- "后到先判" 规则 (LIFO 顺序)
- 无懈可击拦截点
- 闪电传递与雷电伤害

所有方法依赖 GameContext 协议而非 GameEngine 具体类。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from i18n import t as _t

from .card import CardName, CardSuit

if TYPE_CHECKING:
    from .context import GameContext
    from .player import Player

logger = logging.getLogger(__name__)


class JudgeSystem:
    """判定子系统 — 处理判定阶段的延时锦囊结算。"""

    def __init__(self, ctx: GameContext) -> None:
        self.ctx = ctx

    # ==================== 判定阶段 ====================

    def phase_judge(self, player: Player) -> None:
        """判定阶段：依次处理判定区的延时锦囊。

        规则: "后到先判" — judge_area[0] 是最后放入的，先判定。
        每张延时锦囊判定前均有无懈可击拦截点。
        """
        ctx = self.ctx

        while player.judge_area:
            card = player.judge_area.pop(0)
            ctx.log_event("judge", _t("judge.begin", name=player.name, card=card.name))

            # 无懈可击拦截 (延时锦囊, source=判定者)
            if ctx._request_wuxie(card, player, player, is_delay=True):
                ctx.log_event("effect", _t("resolver.nullified", card=card.name))
                ctx.deck.discard([card])
                continue

            # 翻开牌堆顶作为判定牌
            judge_cards = ctx.deck.draw(1)
            if not judge_cards:
                ctx.log_event("error", _t("judge.deck_empty"))
                ctx.deck.discard([card])
                continue

            judge_card = judge_cards[0]
            ctx.log_event("judge", _t("judge.result", card=judge_card.display_name))

            # 按延时锦囊类型分派结算
            if card.name == CardName.LEBUSISHU:
                self._resolve_lebusishu(player, judge_card)
            elif card.name == CardName.BINGLIANG:
                self._resolve_bingliang(player, judge_card)
            elif card.name == CardName.SHANDIAN:
                if self._resolve_shandian(player, card, judge_card):
                    continue  # 闪电传递, 不进弃牌堆

            # 判定牌和延时锦囊进弃牌堆
            ctx.deck.discard([judge_card, card])

    # ==================== 各延时锦囊结算 ====================

    def _resolve_lebusishu(self, player: Player, judge_card: object) -> None:
        """乐不思蜀: 非红桃 → 跳过出牌阶段。"""
        ctx = self.ctx
        if judge_card.suit != CardSuit.HEART:
            ctx.log_event("effect", _t("judge.lebusishu_fail", name=player.name))
            player.skip_play_phase = True
        else:
            ctx.log_event("effect", _t("judge.lebusishu_success", name=player.name))

    def _resolve_bingliang(self, player: Player, judge_card: object) -> None:
        """兵粮寸断: 非梅花 → 跳过摸牌阶段。"""
        ctx = self.ctx
        if judge_card.suit != CardSuit.CLUB:
            ctx.log_event("effect", _t("judge.bingliang_fail", name=player.name))
            player.skip_draw_phase = True
        else:
            ctx.log_event("effect", _t("judge.bingliang_success", name=player.name))

    def _resolve_shandian(self, player: Player, card: object, judge_card: object) -> bool:
        """闪电: 黑桃 2-9 → 3 点雷电伤害; 否则传递给下家。

        返回 True 表示闪电传递 (不进弃牌堆), False 表示命中 (进弃牌堆)。
        """
        ctx = self.ctx

        if judge_card.suit == CardSuit.SPADE and 2 <= judge_card.number <= 9:
            ctx.log_event("effect", _t("judge.shandian_hit", name=player.name))
            ctx.deal_damage(None, player, 3, "thunder")
            return False  # 闪电命中, 进弃牌堆

        # 未命中 → 传递给下一个没有闪电的存活玩家
        ctx.log_event("effect", _t("judge.shandian_dodge", name=player.name))
        receiver = self._find_lightning_receiver(player)
        if receiver:
            receiver.judge_area.insert(0, card)
            ctx.log_event("effect", _t("judge.shandian_pass", name=receiver.name))
            ctx.deck.discard([judge_card])
            return True  # 闪电传递, 不进弃牌堆

        # 没有合法接收者，闪电进弃牌堆
        logger.debug("No valid receiver for Lightning, discarding")
        return False

    def _find_lightning_receiver(self, current: Player) -> Player | None:
        """找到下一个可以接收闪电的玩家。

        跳过死亡玩家和已有闪电的玩家。
        如果绕一圈回到自己或无合法目标，返回 None。
        """
        ctx = self.ctx
        alive = ctx.get_alive_players()
        if len(alive) <= 1:
            return None

        try:
            start_idx = alive.index(current)
        except ValueError:
            return None

        for i in range(1, len(alive)):
            candidate = alive[(start_idx + i) % len(alive)]
            # 跳过已有闪电的玩家
            has_lightning = any(c.name == CardName.SHANDIAN for c in candidate.judge_area)
            if not has_lightning:
                return candidate

        return None  # 所有玩家都已有闪电
