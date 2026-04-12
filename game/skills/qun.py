"""群雄武将技能处理器.

包含以下武将技能：
  吕布 - 无双(wushuang)
  华佗 - 青囊(qingnang)、急救(jijiu)
  貂蝉 - 离间(lijian)、闭月(biyue)
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


# ==================== 吕布 ====================


@skill_handler("wushuang")
def handle_wushuang(player: Player, engine: GameEngine, **kwargs) -> bool:
    """无双：锁定技，使用杀需要两张闪，决斗需要两张杀（此技能在杀/决斗结算时自动生效）."""
    return True


# ==================== 谋袁术 ====================


@skill_handler("jinming")
def handle_jinming(
    player: Player, engine: GameEngine, mode: str = "choose", option: int | None = None, **kwargs
) -> bool:
    """矜名：回合开始选项，回合结束按记录结算条件并可能删除选项."""
    state = player.get_skill_state("jinming")
    deleted_options = set(state.get("deleted_options", set()))

    if mode == "choose":
        available_options = [
            candidate for candidate in (1, 2, 3, 4) if candidate not in deleted_options
        ]
        if not available_options:
            state["current_option"] = None
            return False

        preferred_option = state.get("preferred_option")
        if option is None and preferred_option in available_options:
            option = preferred_option
        if option not in available_options:
            option = available_options[0]

        state["current_option"] = option
        state["last_recorded_option"] = option
        engine.log_event("skill", f"{player.name}发动【矜名】，选择了选项{option}")
        return True

    if mode != "resolve":
        return False

    current_option = state.get("current_option")
    if current_option is None:
        return False

    draw_count = int(current_option)
    cards = engine.deck.draw(draw_count)
    if cards:
        player.draw_cards(cards)
        engine.notify_cards_obtained(player, cards, source=player, reason="jinming")
    engine.log_event("skill", f"{player.name}的【矜名】结算，摸了{draw_count}张牌")

    recovered_hp = player.get_turn_flag("recovered_hp_amount", 0)
    dealt_damage = player.get_turn_flag("dealt_damage_total", 0)
    used_card_types = set(player.get_turn_flag("used_card_types", set()))
    discarded_cards = player.get_turn_flag("discarded_card_count", 0)
    condition_met = {
        1: recovered_hp >= 1,
        2: dealt_damage >= 2,
        3: len(used_card_types) >= 3,
        4: discarded_cards >= 4,
    }.get(current_option, False)

    if not condition_met:
        deleted_options.add(current_option)
        state["deleted_options"] = deleted_options
        player.hp -= 1
        engine.log_event(
            "skill", f"{player.name}未满足【矜名】条件，失去1点体力并删除选项{current_option}"
        )
        if player.hp <= 0:
            player.is_dying = True
            engine._handle_dying(player)

    return True


@skill_handler("xiaoshi")
def handle_xiaoshi(
    player: Player,
    engine: GameEngine,
    card: Card | None = None,
    targets: list[Player] | None = None,
    extra_target: Player | None = None,
    **kwargs,
) -> bool:
    """枭噬：为记录值对应攻击范围的角色追加目标并令其摸牌."""
    from ..card import CardSubtype, CardType

    if player.get_turn_flag("xiaoshi_used", False):
        return False
    if not card or not targets or engine.phase.value != "play":
        return False
    if card.card_type not in (CardType.BASIC, CardType.TRICK):
        return False
    if card.card_type == CardType.TRICK and card.subtype == CardSubtype.DELAY:
        return False

    jinming_state = player.get_skill_state("jinming")
    record_value = jinming_state.get("current_option") or jinming_state.get("last_recorded_option")
    if not record_value:
        return False

    candidates = [
        target
        for target in engine.get_other_players(player)
        if target not in targets and target.equipment.attack_range == record_value
    ]
    if extra_target and extra_target in candidates:
        chosen_target = extra_target
    elif candidates:
        chosen_target = candidates[0]
    else:
        return False

    targets.append(chosen_target)
    drawn_cards = engine.deck.draw(record_value)
    if drawn_cards:
        chosen_target.draw_cards(drawn_cards)
        engine.notify_cards_obtained(
            chosen_target,
            drawn_cards,
            source=player,
            from_player=None,
            reason="xiaoshi",
        )
    player.set_turn_flag("xiaoshi_used", True)
    engine.log_event(
        "skill",
        f"{player.name}发动【枭噬】，额外指定{chosen_target.name}并令其摸{record_value}张牌",
    )
    return True


@skill_handler("yanliang")
def handle_yanliang(
    player: Player,
    engine: GameEngine,
    donor: Player | None = None,
    card: Card | None = None,
    **kwargs,
) -> bool:
    """厌粱：其他群势力角色交给主公装备牌，视为使用一张酒."""
    from ..card import Card, CardName, CardSubtype, CardType
    from ..hero import Kingdom
    from ..player import Identity

    if player.identity != Identity.LORD or donor is None or donor == player or donor.hero is None:
        return False
    if donor.hero.kingdom != Kingdom.QUN or donor.get_turn_flag("yanliang_used", False):
        return False

    if card is None:
        equipment_cards = [
            candidate for candidate in donor.hand if candidate.card_type == CardType.EQUIPMENT
        ]
        if not equipment_cards:
            return False
        card = equipment_cards[0]
    if card not in donor.hand or card.card_type != CardType.EQUIPMENT:
        return False

    donor.remove_card(card)
    engine.notify_cards_lost(donor, [card], source=donor, to_player=player, reason="yanliang")
    player.draw_cards([card])
    engine.notify_cards_obtained(player, [card], source=donor, from_player=donor, reason="yanliang")

    virtual_jiu = Card(
        id=f"virtual_yanliang_jiu_{card.id}",
        name=CardName.JIU,
        card_type=CardType.BASIC,
        subtype=CardSubtype.ALCOHOL,
        suit=card.suit,
        number=card.number,
    )
    donor.set_turn_flag("yanliang_used", True)
    engine.log_event(
        "skill", f"{donor.name}响应{player.name}的【厌粱】，交出{card.display_name}并视为使用【酒】"
    )
    return engine.card_resolver.use_jiu(donor, virtual_jiu)


# ==================== 界刘表 ====================


@skill_handler("zishou")
def handle_zishou(
    player: Player,
    engine: GameEngine,
    mode: str = "draw",
    cards: list[Card] | None = None,
    **kwargs,
) -> bool:
    """自守：摸牌阶段额外摸牌，若本回合造成过伤害则结束阶段弃牌."""
    extra_count = engine.count_alive_kingdoms()
    if extra_count <= 0:
        return False

    if mode == "draw":
        if player.get_turn_flag("zishou_used", False):
            return False
        drawn_cards = engine.deck.draw(extra_count)
        if drawn_cards:
            player.draw_cards(drawn_cards)
            engine.notify_cards_obtained(player, drawn_cards, source=player, reason="zishou")
        player.set_turn_flag("zishou_used", True)
        player.set_turn_flag("zishou_draw_count", extra_count)
        engine.log_event("skill", f"{player.name}发动【自守】，额外摸了{extra_count}张牌")
        return True

    if mode != "end":
        return False
    if not player.get_turn_flag("zishou_used", False):
        return False
    if not player.get_turn_flag("zishou_damaged_others", False):
        return False

    discard_count = min(
        player.hand_count, int(player.get_turn_flag("zishou_draw_count", extra_count))
    )
    if discard_count <= 0:
        return False

    selected_cards = list(cards or player.hand[:discard_count])[:discard_count]
    if not selected_cards:
        return False
    engine.discard_cards(player, selected_cards)
    engine.log_event("skill", f"{player.name}的【自守】触发，弃置了{len(selected_cards)}张牌")
    return True


@skill_handler("zongshi")
def handle_zongshi(
    player: Player,
    engine: GameEngine,
    source: Player | None = None,
    damage_event=None,
    **kwargs,
) -> bool:
    """宗室：每个势力限一次，防止该势力造成的伤害并令来源摸牌."""
    if source is None or source.hero is None or damage_event is None:
        return False

    state = player.get_skill_state("zongshi")
    prevented_kingdoms = set(state.get("prevented_kingdoms", set()))
    source_kingdom = source.hero.kingdom.value
    if source_kingdom in prevented_kingdoms:
        return False

    damage_event.prevent()
    prevented_kingdoms.add(source_kingdom)
    state["prevented_kingdoms"] = prevented_kingdoms

    drawn_cards = engine.deck.draw(1)
    if drawn_cards:
        source.draw_cards(drawn_cards)
        engine.notify_cards_obtained(source, drawn_cards, source=player, reason="zongshi")
    engine.log_event(
        "skill", f"{player.name}发动【宗室】，防止了来自{source.name}的伤害并令其摸一张牌"
    )
    return True


# ==================== 华佗 ====================


@skill_handler("qingnang")
def handle_qingnang(
    player: Player, engine: GameEngine, target: Player = None, cards: list = None, **kwargs
) -> bool:
    """青囊：出牌阶段限一次，弃置一张手牌，令一名角色回复1点体力."""
    if not cards or not target:
        return False

    card = cards[0]
    if card not in player.hand:
        return False

    player.remove_card(card)
    engine.deck.discard([card])

    healed = target.heal(1)
    engine.log_event(
        "skill", _t("skill_msg.qingnang", name=player.name, target=target.name, healed=healed)
    )
    return True


@skill_handler("jijiu")
def handle_jijiu(player: Player, engine: GameEngine, card: Card = None, **kwargs) -> bool:
    """急救：回合外，可以将一张红色牌当【桃】使用（转化技能，在濒死求桃时检查）."""
    return True


# ==================== 貂蝉 ====================


@skill_handler("lijian")
def handle_lijian(
    player: Player, engine: GameEngine, targets: list[Player] = None, card: Card = None, **kwargs
) -> bool:
    """离间：出牌阶段限一次，弃一牌令两名男性角色决斗."""
    if not card or not targets or len(targets) < 2:
        return False

    player.remove_card(card)
    engine.deck.discard([card])

    target1, target2 = targets[0], targets[1]
    engine.log_event(
        "skill",
        _t("skill_msg.lijian", name=player.name, target1=target1.name, target2=target2.name),
    )

    engine.combat.use_juedou_forced(target1, target2)
    return True


@skill_handler("biyue")
def handle_biyue(player: Player, engine: GameEngine, **kwargs) -> bool:
    """闭月：结束阶段摸一张牌."""
    cards = engine.deck.draw(1)
    player.draw_cards(cards)
    engine.log_event("skill", _t("skill_msg.biyue", name=player.name))
    return True


# ==================== 导出 ====================

QUN_HANDLERS: dict[str, Callable[..., bool]] = {
    "wushuang": handle_wushuang,
    "jinming": handle_jinming,
    "xiaoshi": handle_xiaoshi,
    "yanliang": handle_yanliang,
    "zishou": handle_zishou,
    "zongshi": handle_zongshi,
    "qingnang": handle_qingnang,
    "jijiu": handle_jijiu,
    "lijian": handle_lijian,
    "biyue": handle_biyue,
}
