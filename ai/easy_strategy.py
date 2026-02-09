"""简单 AI 策略 — 随机出牌

实现 AIStrategy 协议，用于 EASY 难度。
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from game.card import CardName, CardType
from game.config import get_config

from .strategy import is_enemy

if TYPE_CHECKING:
    from game.card import Card
    from game.engine import GameEngine
    from game.player import Player


class EasyStrategy:
    """简单模式策略：随机出牌"""

    def play_phase(self, player: Player, engine: GameEngine) -> None:
        """简单模式：随机出牌"""
        cfg = get_config()
        max_actions = cfg.ai_max_actions
        actions = 0

        while actions < max_actions:
            actions += 1

            if not player.hand:
                break

            # 随机选择一张牌
            card = random.choice(player.hand)

            # 尝试使用
            if self._try_use_card(player, card, engine):
                continue

            # 50%概率结束回合
            if random.random() < 0.5:
                break

    def choose_discard(self, player: Player, count: int,
                       engine: GameEngine) -> list[Card]:
        """简单模式：随机弃牌"""
        if not player.hand:
            return []
        return random.sample(player.hand, min(count, len(player.hand)))

    def should_use_qinglong(self, player: Player, target: Player,
                            engine: GameEngine) -> bool:
        """简单模式：有杀且是敌人就继续"""
        sha_count = len(player.get_cards_by_name(CardName.SHA))
        if sha_count > 1:
            return is_enemy(player, target)
        return False

    # ==================== 内部方法 ====================

    def _try_use_card(self, player: Player, card: Card,
                      engine: GameEngine) -> bool:
        """简单模式：尝试使用卡牌"""
        # 装备牌直接使用
        if card.card_type == CardType.EQUIPMENT:
            return engine.use_card(player, card)

        # 自用锦囊
        if card.name in [CardName.WUZHONG, CardName.TAOYUAN]:
            return engine.use_card(player, card)

        # 桃（需要时使用）
        if card.name == CardName.TAO:
            if player.hp < player.max_hp:
                return engine.use_card(player, card)
            return False

        # 需要目标的牌
        if card.name == CardName.SHA:
            if player.can_use_sha():
                targets = engine.get_targets_in_range(player)
                if targets:
                    target = random.choice(targets)
                    return engine.use_card(player, card, [target])

        elif card.name in [CardName.JUEDOU, CardName.GUOHE]:
            others = engine.get_other_players(player)
            valid_targets = [t for t in others
                             if t.has_any_card() or card.name != CardName.GUOHE]
            if valid_targets:
                target = random.choice(valid_targets)
                return engine.use_card(player, card, [target])

        elif card.name == CardName.SHUNSHOU:
            others = engine.get_other_players(player)
            valid_targets = [t for t in others
                             if engine.calculate_distance(player, t) <= 1
                             and t.has_any_card()]
            if valid_targets:
                target = random.choice(valid_targets)
                return engine.use_card(player, card, [target])

        elif card.name in [CardName.NANMAN, CardName.WANJIAN]:
            return engine.use_card(player, card)

        return False
