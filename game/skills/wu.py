"""吴国武将技能处理器

包含以下武将技能：
  孙权 - 制衡(zhiheng)、救援(jiuyuan)
  周瑜 - 英姿(yingzi)、反间(fanjian)
  大乔 - 国色(guose)、流离(liuli)
  甘宁 - 奇袭(qixi)
  吕蒙 - 克己(keji)
  黄盖 - 苦肉(kurou)
  孙尚香 - 结姻(jieyin)、枭姬(xiaoji)
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


# ==================== 孙权 ====================

@skill_handler("zhiheng")
def handle_zhiheng(player: Player, engine: GameEngine,
                   cards: list[Card] | None = None, **kwargs) -> bool:
    """制衡：弃置任意数量的牌，然后摸等量的牌"""
    if not cards:
        return False

    discard_count = len(cards)

    for card in cards:
        if card in player.hand:
            player.remove_card(card)
            engine.deck.discard([card])

    new_cards = engine.deck.draw(discard_count)
    player.draw_cards(new_cards)

    engine.log_event("skill", _t("skill_msg.zhiheng", name=player.name, discard=discard_count, draw=len(new_cards)))
    return True


@skill_handler("jiuyuan")
def handle_jiuyuan(player: Player, engine: GameEngine, **kwargs) -> bool:
    """救援：锁定技，其他吴势力角色对你使用桃时，额外回复1点体力（此技能在使用桃时自动触发）"""
    return True


# ==================== 周瑜 ====================

@skill_handler("yingzi")
def handle_yingzi(player: Player, engine: GameEngine, **kwargs) -> bool:
    """英姿：摸牌阶段多摸一张牌（此技能在摸牌阶段自动触发）"""
    return True


@skill_handler("fanjian")
def handle_fanjian(player: Player, engine: GameEngine,
                   targets: list[Player] | None = None,
                   cards: list[Card] | None = None, **kwargs) -> bool:
    """反间：选择一名角色，展示一张手牌，让其猜花色"""
    if not targets or not cards:
        return False

    target = targets[0]
    card = cards[0]

    if card not in player.hand:
        return False

    engine.log_event("skill", _t("skill_msg.fanjian", name=player.name, target=target.name))

    guessed_suit = engine.request_handler.choose_suit(target)
    engine.log_event("skill", _t("skill_msg.fanjian_guess", name=target.name, suit=guessed_suit.symbol))

    player.remove_card(card)
    target.draw_cards([card])

    engine.log_event("skill", _t("skill_msg.fanjian_show", card=card.display_name))

    if card.suit != guessed_suit:
        engine.log_event("skill", _t("skill_msg.fanjian_hit", name=target.name))
        engine.deal_damage(player, target, 1)
    else:
        engine.log_event("skill", _t("skill_msg.fanjian_miss", name=target.name))

    return True


# ==================== 大乔 ====================

@skill_handler("guose")
def handle_guose(player: Player, engine: GameEngine,
                 card: Card = None, target: Player = None,
                 targets: list = None, cards: list = None, **kwargs) -> bool:
    """国色：出牌阶段，可以将一张方块牌当【乐不思蜀】使用"""
    from ..card import Card, CardName, CardSubtype, CardSuit, CardType

    if target is None and targets:
        target = targets[0]
    if card is None and cards:
        card = cards[0]

    if not card or not target:
        if player.is_ai:
            diamond_cards = [c for c in player.hand if c.suit == CardSuit.DIAMOND]
            if not diamond_cards:
                return False
            card = diamond_cards[0]
            others = engine.get_other_players(player)
            valid = [t for t in others if t.is_alive
                     and not any(c.name == CardName.LEBUSISHU for c in t.judge_area)]
            if not valid:
                return False
            target = valid[0]
        else:
            return False

    if card.suit != CardSuit.DIAMOND:
        return False

    if any(c.name == CardName.LEBUSISHU for c in target.judge_area):
        engine.log_event("error", _t("resolver.delay_exists", name=target.name, card=_t("card.lebusishu")))
        return False

    if card in player.hand:
        player.remove_card(card)
    else:
        engine.equipment_sys.remove(player, card)
    engine.deck.discard([card])

    virtual_lebu = Card(
        id=f"virtual_lebu_{card.id}",
        name=CardName.LEBUSISHU,
        card_type=CardType.TRICK,
        subtype=CardSubtype.DELAY,
        suit=card.suit,
        number=card.number,
    )
    target.judge_area.insert(0, virtual_lebu)
    engine.log_event("skill",
        _t("skill_msg.guose", name=player.name, card=card.display_name, target=target.name))
    return True


@skill_handler("liuli")
def handle_liuli(player: Player, engine: GameEngine,
                 new_target: Player = None, **kwargs) -> bool:
    """流离：成为杀的目标时，可以弃置一张牌并选择攻击范围内的一名其他角色，将此杀转移给该角色"""
    if new_target is None or not player.hand:
        return False

    card = player.hand[0]
    player.remove_card(card)
    engine.deck.discard([card])

    engine.log_event("skill", _t("skill_msg.liuli", name=player.name, target=new_target.name))
    return True


# ==================== 甘宁 ====================

@skill_handler("qixi")
def handle_qixi(player: Player, engine: GameEngine,
                card: Card = None, target: Player = None,
                targets: list = None, cards: list = None, **kwargs) -> bool:
    """奇袭：出牌阶段，可以将任意黑色牌当【过河拆桥】使用，可以被无懈可击抵消"""
    from ..card import Card, CardName, CardSubtype, CardType

    if target is None and targets:
        target = targets[0]
    if card is None and cards:
        card = cards[0]

    if not card or not target:
        if player.is_ai:
            black_cards = [c for c in player.hand if c.is_black]
            if not black_cards:
                return False
            card = black_cards[0]
            others = engine.get_other_players(player)
            valid = [t for t in others if t.is_alive and t.has_any_card()]
            if not valid:
                return False
            target = valid[0]
        else:
            return False

    if not card.is_black:
        return False

    if not target.has_any_card():
        engine.log_event("error", _t("resolver.no_cards_dismantle", name=target.name))
        return False

    if card in player.hand:
        player.remove_card(card)
    else:
        engine.equipment_sys.remove(player, card)
    engine.deck.discard([card])

    engine.log_event("skill",
        _t("skill_msg.qixi", name=player.name, card=card.display_name, target=target.name))

    virtual_guohe = Card(
        id=f"virtual_guohe_{card.id}",
        name=CardName.GUOHE,
        card_type=CardType.TRICK,
        subtype=CardSubtype.SINGLE_TARGET,
        suit=card.suit,
        number=card.number,
    )

    if engine.combat.request_wuxie(virtual_guohe, player, target):
        engine.log_event("effect", _t("skill_msg.qixi_nullified"))
        return True

    discarded = engine.card_resolver.choose_and_discard_card(player, target)
    if discarded:
        engine.log_event("effect", _t("resolver.card_discarded", name=target.name, card=discarded.display_name))
    return True


# ==================== 吕蒙 ====================

@skill_handler("keji")
def handle_keji(player: Player, engine: GameEngine, **kwargs) -> bool:
    """克己：若出牌阶段未使用杀，跳过弃牌阶段"""
    if player.sha_count == 0:
        engine.log_event("skill", _t("skill_msg.keji", name=player.name))
        return True
    return False


# ==================== 黄盖 ====================

@skill_handler("kurou")
def handle_kurou(player: Player, engine: GameEngine, **kwargs) -> bool:
    """苦肉：出牌阶段，失去1点体力摸两张牌。原版规则：允许 hp=1 时发动进入濒死，被救后摸牌"""
    player.hp -= 1
    engine.log_event("skill", _t("skill_msg.kurou", name=player.name))

    if player.hp <= 0:
        player.is_dying = True
        saved = engine._handle_dying(player)
        if not saved:
            engine._handle_death(player)
            return True

    if player.is_alive:
        cards = engine.deck.draw(2)
        player.draw_cards(cards)
        engine.log_event("skill", _t("resolver.drew_cards", name=player.name, count=2))
    return True


# ==================== 孙尚香 ====================

@skill_handler("jieyin")
def handle_jieyin(player: Player, engine: GameEngine,
                  target: Player = None, cards: list[Card] = None, **kwargs) -> bool:
    """结姻：弃两张手牌，自己和一名受伤男性各回复1点体力"""
    if not target or not cards or len(cards) < 2:
        return False

    if target.gender != "male" or target.hp >= target.max_hp:
        return False

    for card in cards:
        player.remove_card(card)
    engine.deck.discard(cards)

    player.heal(1)
    target.heal(1)
    engine.log_event("skill", _t("skill_msg.jieyin", name=player.name, target=target.name))
    return True


@skill_handler("xiaoji")
def handle_xiaoji(player: Player, engine: GameEngine, **kwargs) -> bool:
    """枭姬：失去装备区的牌后摸两张牌"""
    cards = engine.deck.draw(2)
    player.draw_cards(cards)
    engine.log_event("skill", _t("skill_msg.xiaoji", name=player.name))
    return True


# ==================== 导出 ====================

WU_HANDLERS: dict[str, Callable[..., bool]] = {
    "zhiheng": handle_zhiheng,
    "jiuyuan": handle_jiuyuan,
    "yingzi": handle_yingzi,
    "fanjian": handle_fanjian,
    "guose": handle_guose,
    "liuli": handle_liuli,
    "qixi": handle_qixi,
    "keji": handle_keji,
    "kurou": handle_kurou,
    "jieyin": handle_jieyin,
    "xiaoji": handle_xiaoji,
}
