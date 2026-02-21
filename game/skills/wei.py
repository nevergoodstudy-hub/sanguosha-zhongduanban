"""魏国武将技能处理器

包含以下武将技能：
  曹操 - 奸雄(jianxiong)、护驾(hujia)
  司马懿 - 反馈(fankui)、鬼才(guicai)
  夏侯惇 - 刚烈(ganglie)
  张辽 - 突袭(tuxi)
  徐晃 - 断粮(duanliang)
  曹仁 - 据守(jushou)
  夏侯渊 - 神速(shensu)
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from .registry import skill_handler

if TYPE_CHECKING:
    from ..card import Card
    from ..engine import GameEngine
    from ..player import Player


# ==================== 曹操 ====================


@skill_handler("jianxiong")
def handle_jianxiong(
    player: Player, engine: GameEngine, damage_card: Card | None = None, **kwargs
) -> bool:
    """奸雄：受到伤害后，可以获得造成伤害的牌"""
    if damage_card:
        if damage_card in engine.deck.discard_pile:
            engine.deck.discard_pile.remove(damage_card)
            player.draw_cards([damage_card])
            engine.log_event(
                "skill", _t("skill_msg.jianxiong", name=player.name, card=damage_card.display_name)
            )
            return True
    return False


@skill_handler("hujia")
def handle_hujia(player: Player, engine: GameEngine, **kwargs) -> bool:
    """护驾：主公技，让其他魏势力角色代替出闪"""
    from ..card import CardName
    from ..hero import Kingdom
    from ..player import Identity

    if player.identity != Identity.LORD:
        return False

    for other in engine.get_other_players(player):
        if other.hero and other.hero.kingdom == Kingdom.WEI:
            shan_cards = other.get_cards_by_name(CardName.SHAN)
            if shan_cards:
                if other.is_ai:
                    card = shan_cards[0]
                    other.remove_card(card)
                    engine.deck.discard([card])
                    engine.log_event("skill", _t("skill_msg.hujia", name=other.name))
                    return True
                else:
                    result = engine.request_handler.ask_for_hujia(other)
                    if result:
                        other.remove_card(result)
                        engine.deck.discard([result])
                        engine.log_event("skill", _t("skill_msg.hujia", name=other.name))
                        return True

    return False


# ==================== 司马懿 ====================


@skill_handler("fankui")
def handle_fankui(player: Player, engine: GameEngine, source: Player = None, **kwargs) -> bool:
    """反馈：受到伤害后，可以获得伤害来源的一张牌"""
    if source is None or source == player:
        return False

    if not source.has_any_card():
        return False

    all_cards = source.get_all_cards()
    if all_cards:
        card = random.choice(all_cards)
        if card in source.hand:
            source.remove_card(card)
        else:
            source.equipment.unequip_card(card)
        player.draw_cards([card])
        engine.log_event("skill", _t("skill_msg.fankui", name=player.name, source=source.name))
        return True

    return False


@skill_handler("guicai")
def handle_guicai(player: Player, engine: GameEngine, judge_card: Card = None, **kwargs) -> bool:
    """鬼才：在判定牌生效前，可以打出一张手牌代替之"""
    if not player.hand:
        return False

    if player.is_ai:
        card = player.hand[0]
        player.remove_card(card)
        engine.deck.discard([card])
        engine.log_event("skill", _t("skill_msg.guicai", name=player.name, card=card.display_name))
        return True

    # BUG-008 fix: 人类玩家通过 UI 选择手牌替换判定牌
    ui = engine.ui
    if ui:
        try:
            selected = ui.choose_card_to_play(player)
            if selected:
                player.remove_card(selected)
                engine.deck.discard([selected])
                engine.log_event(
                    "skill", _t("skill_msg.guicai", name=player.name, card=selected.display_name)
                )
                return True
        except Exception:
            pass

    return False


# ==================== 夏侯惇 ====================


@skill_handler("ganglie")
def handle_ganglie(player: Player, engine: GameEngine, source: Player = None, **kwargs) -> bool:
    """刚烈：受到伤害后，可以进行判定，若结果不为红桃，伤害来源须弃置两张手牌或受到1点伤害"""
    if source is None or source == player:
        return False

    judge_card = engine.deck.draw(1)[0]
    engine.log_event(
        "skill", _t("skill_msg.ganglie", name=player.name, card=judge_card.display_name)
    )
    engine.deck.discard([judge_card])

    from ..card import CardSuit

    if judge_card.suit != CardSuit.HEART:
        if source.hand_count >= 2:
            if source.is_ai:
                cards = source.hand[:2]
                for c in cards:
                    source.remove_card(c)
                engine.deck.discard(cards)
                engine.log_event("skill", _t("skill_msg.ganglie_discard", name=source.name))
            else:
                # BUG-007 fix: 人类玩家通过 UI 选择弃两张牌或受到1点伤害
                ui = engine.ui
                chose_discard = False
                if ui:
                    try:
                        cards_to_discard = ui.choose_cards_to_discard(source, 2)
                        if cards_to_discard and len(cards_to_discard) >= 2:
                            for c in cards_to_discard[:2]:
                                source.remove_card(c)
                            engine.deck.discard(cards_to_discard[:2])
                            engine.log_event(
                                "skill", _t("skill_msg.ganglie_discard", name=source.name)
                            )
                            chose_discard = True
                    except Exception:
                        pass
                if not chose_discard:
                    engine.deal_damage(player, source, 1)
        else:
            engine.deal_damage(player, source, 1)
        return True

    return False


# ==================== 张辽 ====================


@skill_handler("tuxi")
def handle_tuxi(player: Player, engine: GameEngine, targets: list = None, **kwargs) -> bool:
    """突袭：摸牌阶段，可以少摸牌，然后获得等量其他角色各一张手牌"""
    if targets is None:
        targets = []

    for target in targets:
        if target.hand:
            card = random.choice(target.hand)
            target.remove_card(card)
            player.draw_cards([card])
            engine.log_event("skill", _t("skill_msg.tuxi", name=player.name, target=target.name))

    return len(targets) > 0


# ==================== 徐晃 ====================


@skill_handler("duanliang")
def handle_duanliang(
    player: Player,
    engine: GameEngine,
    card: Card = None,
    target: Player = None,
    targets: list = None,
    cards: list = None,
    **kwargs,
) -> bool:
    """断粮：出牌阶段，可以将黑色基本牌或装备牌当【兵粮寸断】使用；可以对距离2以内的角色使用"""
    from ..card import Card, CardName, CardSubtype, CardType

    if target is None and targets:
        target = targets[0]
    if card is None and cards:
        card = cards[0]

    if not card or not target:
        if player.is_ai:
            black_cards = [
                c
                for c in player.hand
                if c.is_black and c.card_type in (CardType.BASIC, CardType.EQUIPMENT)
            ]
            if not black_cards:
                return False
            card = black_cards[0]
            others = engine.get_other_players(player)
            valid = [
                t
                for t in others
                if t.is_alive
                and engine.calculate_distance(player, t) <= 2
                and not any(c.name == CardName.BINGLIANG for c in t.judge_area)
            ]
            if not valid:
                return False
            target = valid[0]
        else:
            return False

    if not card.is_black or card.card_type not in (CardType.BASIC, CardType.EQUIPMENT):
        return False

    if engine.calculate_distance(player, target) > 2:
        engine.log_event("error", _t("skill_msg.duanliang_too_far", name=target.name))
        return False

    if any(c.name == CardName.BINGLIANG for c in target.judge_area):
        engine.log_event(
            "error", _t("resolver.delay_exists", name=target.name, card=_t("card.bingliang"))
        )
        return False

    if card in player.hand:
        player.remove_card(card)
    else:
        engine.equipment_sys.remove(player, card)
    engine.deck.discard([card])

    virtual_bl = Card(
        id=f"virtual_bl_{card.id}",
        name=CardName.BINGLIANG,
        card_type=CardType.TRICK,
        subtype=CardSubtype.DELAY,
        suit=card.suit,
        number=card.number,
    )
    target.judge_area.insert(0, virtual_bl)
    engine.log_event(
        "skill",
        _t("skill_msg.duanliang", name=player.name, card=card.display_name, target=target.name),
    )
    return True


# ==================== 曹仁 ====================


@skill_handler("jushou")
def handle_jushou(player: Player, engine: GameEngine, **kwargs) -> bool:
    """据守：结束阶段摸三张牌并翻面"""
    cards = engine.deck.draw(3)
    player.draw_cards(cards)
    player.toggle_flip()
    engine.log_event("skill", _t("skill_msg.jushou", name=player.name))
    return True


# ==================== 夏侯渊 ====================


@skill_handler("shensu")
def handle_shensu(
    player: Player,
    engine: GameEngine,
    target: Player = None,
    choice: int = 1,
    targets: list = None,
    cards: list = None,
    **kwargs,
) -> bool:
    """神速：
    选项1: 跳过判定阶段和摸牌阶段，视为对一名角色使用一张【杀】
    选项2: 跳过出牌阶段并弃置一张装备牌，视为对一名角色使用一张【杀】
    """
    if target is None and targets:
        target = targets[0]

    if not target:
        return False

    if not target.is_alive:
        return False

    engine.log_event(
        "skill", _t("skill_msg.shensu", name=player.name, choice=choice, target=target.name)
    )

    from ..constants import SkillId

    required_shan = 2 if player.has_skill(SkillId.WUSHUANG) else 1
    shan_count = engine.combat.request_shan(target, required_shan)

    if shan_count >= required_shan:
        engine.log_event("dodge", _t("combat.dodge_success", name=target.name))
    else:
        engine.deal_damage(player, target, 1)

    return True


# ==================== 导出 ====================

WEI_HANDLERS: dict[str, Callable[..., bool]] = {
    "jianxiong": handle_jianxiong,
    "hujia": handle_hujia,
    "fankui": handle_fankui,
    "guicai": handle_guicai,
    "ganglie": handle_ganglie,
    "tuxi": handle_tuxi,
    "duanliang": handle_duanliang,
    "jushou": handle_jushou,
    "shensu": handle_shensu,
}
