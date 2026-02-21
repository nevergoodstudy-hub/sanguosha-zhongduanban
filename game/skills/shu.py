"""蜀国武将技能处理器

包含以下武将技能：
  刘备 - 仁德(rende)、激将(jijiang)
  关羽 - 武圣(wusheng)
  张飞 - 咆哮(paoxiao)
  诸葛亮 - 观星(guanxing)、空城(kongcheng)
  赵云 - 龙胆(longdan)
  马超 - 马术(mashu)、铁骑(tieji)
  黄月英 - 集智(jizhi)、奇才(qicai)
  黄忠 - 烈弓(liegong)
  魏延 - 狂骨(kuanggu)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from .registry import skill_handler

if TYPE_CHECKING:
    from ..card import Card
    from ..engine import GameEngine
    from ..player import Player


# ==================== 刘备 ====================


@skill_handler("rende")
def handle_rende(
    player: Player,
    engine: GameEngine,
    targets: list[Player] | None = None,
    cards: list[Card] | None = None,
    **kwargs,
) -> bool:
    """仁德：将任意数量的手牌交给其他角色，每回合给出第二张牌时回复1点体力"""
    if not targets or not cards:
        return False

    target = targets[0]

    transferred_cards = []
    for card in cards:
        if card in player.hand:
            player.remove_card(card)
            transferred_cards.append(card)

    if not transferred_cards:
        return False

    target.draw_cards(transferred_cards)

    cards_str = ", ".join(c.display_name for c in transferred_cards)
    engine.log_event(
        "skill", _t("skill_msg.rende", name=player.name, cards=cards_str, target=target.name)
    )

    rende_count = player.skill_used.get("rende_cards", 0)
    for card in transferred_cards:
        rende_count += 1
        if rende_count == 2 and player.hp < player.max_hp:
            player.heal(1)
            engine.log_event("skill", _t("skill_msg.rende_heal", name=player.name))

    player.skill_used["rende_cards"] = rende_count
    return True


@skill_handler("jijiang")
def handle_jijiang(player: Player, engine: GameEngine, **kwargs) -> bool:
    """激将：主公技，让其他蜀势力角色代替出杀"""
    from ..card import CardName
    from ..hero import Kingdom
    from ..player import Identity

    if player.identity != Identity.LORD:
        return False

    for other in engine.get_other_players(player):
        if other.hero and other.hero.kingdom == Kingdom.SHU:
            sha_cards = other.get_cards_by_name(CardName.SHA)
            if sha_cards:
                if other.is_ai:
                    card = sha_cards[0]
                    other.remove_card(card)
                    engine.deck.discard([card])
                    engine.log_event("skill", _t("skill_msg.jijiang", name=other.name))
                    return True
                else:
                    result = engine.request_handler.ask_for_jijiang(other)
                    if result:
                        other.remove_card(result)
                        engine.deck.discard([result])
                        engine.log_event("skill", _t("skill_msg.jijiang", name=other.name))
                        return True

    return False


# ==================== 关羽 ====================


@skill_handler("wusheng")
def handle_wusheng(player: Player, engine: GameEngine, card: Card | None = None, **kwargs) -> bool:
    """武圣：可以将红色牌当杀使用或打出（转化技能，在请求杀/闪时自动检查）"""
    return True


# ==================== 张飞 ====================


@skill_handler("paoxiao")
def handle_paoxiao(player: Player, engine: GameEngine, **kwargs) -> bool:
    """咆哮：锁定技，出牌阶段使用杀无次数限制（在can_use_sha中自动检查）"""
    return True


# ==================== 诸葛亮 ====================


@skill_handler("guanxing")
def handle_guanxing(player: Player, engine: GameEngine, **kwargs) -> bool:
    """观星：准备阶段，观看牌堆顶X张牌（X为存活角色数，最多5张）"""
    alive_count = len(engine.get_alive_players())
    look_count = min(5, alive_count)

    cards = engine.deck.peek(look_count)
    if not cards:
        return False

    engine.log_event("skill", _t("skill_msg.guanxing", name=player.name, count=len(cards)))

    top_cards, bottom_cards = engine.request_handler.guanxing_selection(player, cards)

    for _ in range(len(cards)):
        engine.deck.draw_pile.pop()

    if player.is_ai:
        engine.deck.put_on_top(top_cards)
        engine.deck.put_on_bottom(bottom_cards)
    else:
        engine.deck.put_on_top(list(reversed(top_cards)))
        engine.deck.put_on_bottom(bottom_cards)

    return True


@skill_handler("kongcheng")
def handle_kongcheng(player: Player, engine: GameEngine, **kwargs) -> bool:
    """空城：锁定技，若没有手牌，不是杀和决斗的合法目标"""
    return player.hand_count == 0


# ==================== 赵云 ====================


@skill_handler("longdan")
def handle_longdan(player: Player, engine: GameEngine, **kwargs) -> bool:
    """龙胆：可以将杀当闪使用或打出，或将闪当杀使用或打出（转化技能）"""
    return True


# ==================== 马超 ====================


@skill_handler("mashu")
def handle_mashu(player: Player, engine: GameEngine, **kwargs) -> bool:
    """马术：锁定技，计算与其他角色的距离-1（在距离计算时自动生效）"""
    return True


@skill_handler("tieji")
def handle_tieji(player: Player, engine: GameEngine, target: Player = None, **kwargs) -> bool:
    """铁骑：使用杀指定目标后，可以进行判定，若结果为红色，目标不能使用闪"""
    if target is None:
        return False

    judge_card = engine.deck.draw(1)[0]
    engine.log_event("skill", _t("skill_msg.tieji", name=player.name, card=judge_card.display_name))
    engine.deck.discard([judge_card])

    if judge_card.is_red:
        engine.log_event("skill", _t("skill_msg.tieji_red", name=target.name))
        return True

    return False


# ==================== 黄月英 ====================


@skill_handler("jizhi")
def handle_jizhi(player: Player, engine: GameEngine, **kwargs) -> bool:
    """集智：使用非延时锦囊牌时，可以摸一张牌"""
    cards = engine.deck.draw(1)
    player.draw_cards(cards)
    engine.log_event("skill", _t("skill_msg.jizhi", name=player.name))
    return True


@skill_handler("qicai")
def handle_qicai(player: Player, engine: GameEngine, **kwargs) -> bool:
    """奇才：锁定技，使用锦囊牌无距离限制（在使用锦囊牌时自动生效）"""
    return True


# ==================== 黄忠 ====================


@skill_handler("liegong")
def handle_liegong(player: Player, engine: GameEngine, target: Player = None, **kwargs) -> bool:
    """烈弓：使用杀时，若目标手牌数>=你体力值或<=你攻击范围，其不能闪避"""
    if not target:
        return False

    target_hand = target.hand_count
    player_hp = player.hp
    attack_range = player.equipment.attack_range

    if target_hand >= player_hp or target_hand <= attack_range:
        engine.log_event("skill", _t("skill_msg.liegong", name=player.name, target=target.name))
        return True
    return False


# ==================== 魏延 ====================


@skill_handler("kuanggu")
def handle_kuanggu(
    player: Player, engine: GameEngine, target: Player = None, damage: int = 1, **kwargs
) -> bool:
    """狂骨：对距离1以内的角色造成伤害后回复1点体力"""
    if not target:
        return False

    distance = engine.calculate_distance(player, target)
    if distance <= 1 and player.hp < player.max_hp:
        player.heal(1)
        engine.log_event("skill", _t("skill_msg.kuanggu", name=player.name))
        return True
    return False


# ==================== 导出 ====================

SHU_HANDLERS: dict[str, Callable[..., bool]] = {
    "rende": handle_rende,
    "jijiang": handle_jijiang,
    "wusheng": handle_wusheng,
    "paoxiao": handle_paoxiao,
    "guanxing": handle_guanxing,
    "kongcheng": handle_kongcheng,
    "longdan": handle_longdan,
    "mashu": handle_mashu,
    "tieji": handle_tieji,
    "jizhi": handle_jizhi,
    "qicai": handle_qicai,
    "liegong": handle_liegong,
    "kuanggu": handle_kuanggu,
}
