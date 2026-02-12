"""AI 策略协议与共享工具函数

Phase 4.1: 将 AI 决策逻辑按策略模式拆分，
各难度策略实现此 Protocol，AIBot 作为薄协调器委托。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from game.card import CardName, CardType
from game.player import Identity

if TYPE_CHECKING:
    from game.card import Card
    from game.engine import GameEngine  # 也用于 is_enemy() 的 engine 参数类型
    from game.player import Player


class AIStrategy(Protocol):
    """AI 策略协议 — 各难度共用接口"""

    def play_phase(self, player: Player, engine: GameEngine) -> None:
        """出牌阶段决策"""
        ...

    def choose_discard(self, player: Player, count: int,
                       engine: GameEngine) -> list[Card]:
        """选择弃牌"""
        ...

    def should_use_qinglong(self, player: Player, target: Player,
                            engine: GameEngine) -> bool:
        """决定是否使用青龙偃月刀继续攻击"""
        ...


# ==================== 共享工具函数 ====================

def is_enemy(player: Player, target: Player,
             *, engine: GameEngine | None = None) -> bool:
    """判断目标是否为敌人

    Args:
        player: 判断主体
        target: 目标玩家
        engine: 可选，提供后可获取精确的存活人数（影响间谍策略）
    """
    my_identity = player.identity
    target_identity = target.identity

    if my_identity == Identity.LORD or my_identity == Identity.LOYALIST:
        return target_identity in [Identity.REBEL, Identity.SPY]
    elif my_identity == Identity.REBEL:
        return target_identity in [Identity.LORD, Identity.LOYALIST]
    elif my_identity == Identity.SPY:
        # BUG-FIX: 之前只计算 player+target 两人，永远为 2，导致间谍始终视所有人为敌
        if engine is not None:
            alive_count = len(engine.get_alive_players())
        else:
            # 无 engine 时保守估计：假设非最终对决阶段
            alive_count = 3
        if alive_count <= 2:
            return True  # 最后单挑阶段，所有人都是敌人
        # 前期帮主公清反贼，中期帮反贼削弱主公阵营
        return target_identity == Identity.REBEL

    return False


def get_friends(player: Player, engine: GameEngine) -> list[Player]:
    """获取友方玩家"""
    return [p for p in engine.get_other_players(player) if not is_enemy(player, p)]


def card_priority(card: Card) -> int:
    """卡牌保留优先级（低值先弃）"""
    if card.name == CardName.TAO:
        return 100  # 最高优先级保留
    elif card.name == CardName.WUXIE:
        return 90
    elif card.name == CardName.WUZHONG:
        return 80
    elif card.name == CardName.SHAN:
        return 70
    elif card.name == CardName.SHA:
        return 60
    elif card.card_type == CardType.EQUIPMENT:
        return 30  # 装备优先级低（应该已经装上了）
    else:
        return 50


def smart_discard(player: Player, count: int) -> list[Card]:
    """智能弃牌 — 按优先级保留高价值牌"""
    if not player.hand:
        return []

    def _priority(card: Card) -> int:
        p = card_priority(card)
        # 如果不能用杀了，杀优先弃掉
        if card.name == CardName.SHA and not player.can_use_sha():
            return 20
        return p

    sorted_cards = sorted(player.hand, key=_priority)
    return sorted_cards[:count]


def pick_least_valuable(cards: list, player: Player) -> Card:
    """从候选牌中选价值最低的牌作为转化素材"""
    def card_value(card: Card) -> int:
        if card.name == CardName.TAO:
            return 100
        elif card.name == CardName.WUXIE:
            return 90
        elif card.name == CardName.SHAN:
            return 70
        elif card.name == CardName.SHA:
            return 40 if player.can_use_sha() else 15
        elif card.card_type == CardType.EQUIPMENT:
            return 25
        return 50
    cards_sorted = sorted(cards, key=card_value)
    return cards_sorted[0]


def count_useless_cards(player: Player, engine: GameEngine) -> int:
    """计算无用卡牌数量"""
    useless = 0
    for card in player.hand:
        if card.name == CardName.SHAN:
            useless += max(0, len(player.get_cards_by_name(CardName.SHAN)) - 2)
        elif card.name == CardName.SHA:
            if not player.can_use_sha():
                useless += 1
    return useless
