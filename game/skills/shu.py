"""蜀国武将技能处理器.

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

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from ai.strategy import get_friends, is_enemy, pick_least_valuable
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
    """仁德：将任意数量的手牌交给其他角色，每回合给出第二张牌时回复1点体力."""
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
    for _card in transferred_cards:
        rende_count += 1
        if rende_count == 2 and player.hp < player.max_hp:
            player.heal(1)
            engine.log_event("skill", _t("skill_msg.rende_heal", name=player.name))

    player.skill_used["rende_cards"] = rende_count
    return True


@skill_handler("jijiang")
def handle_jijiang(player: Player, engine: GameEngine, **kwargs) -> bool:
    """激将：主公技，让其他蜀势力角色代替出杀."""
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
    """武圣：可以将红色牌当杀使用或打出（转化技能，在请求杀/闪时自动检查）."""
    return True


# ==================== 张飞 ====================


@skill_handler("paoxiao")
def handle_paoxiao(player: Player, engine: GameEngine, **kwargs) -> bool:
    """咆哮：锁定技，出牌阶段使用杀无次数限制（在can_use_sha中自动检查）."""
    return True


# ==================== 诸葛亮 ====================


@skill_handler("guanxing")
def handle_guanxing(player: Player, engine: GameEngine, **kwargs) -> bool:
    """观星：准备阶段，观看牌堆顶X张牌（X为存活角色数，最多5张）."""
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
    """空城：锁定技，若没有手牌，不是杀和决斗的合法目标."""
    return player.hand_count == 0


# ==================== 赵云 ====================


@skill_handler("longdan")
def handle_longdan(player: Player, engine: GameEngine, **kwargs) -> bool:
    """龙胆：可以将杀当闪使用或打出，或将闪当杀使用或打出（转化技能）."""
    return True


# ==================== 马超 ====================


@skill_handler("mashu")
def handle_mashu(player: Player, engine: GameEngine, **kwargs) -> bool:
    """马术：锁定技，计算与其他角色的距离-1（在距离计算时自动生效）."""
    return True


@skill_handler("tieji")
def handle_tieji(player: Player, engine: GameEngine, target: Player = None, **kwargs) -> bool:
    """铁骑：使用杀指定目标后，可以进行判定，若结果为红色，目标不能使用闪."""
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
    """集智：使用非延时锦囊牌时，可以摸一张牌."""
    cards = engine.deck.draw(1)
    player.draw_cards(cards)
    engine.log_event("skill", _t("skill_msg.jizhi", name=player.name))
    return True


@skill_handler("qicai")
def handle_qicai(player: Player, engine: GameEngine, **kwargs) -> bool:
    """奇才：锁定技，使用锦囊牌无距离限制（在使用锦囊牌时自动生效）."""
    return True


# ==================== 黄忠 ====================


@skill_handler("liegong")
def handle_liegong(player: Player, engine: GameEngine, target: Player = None, **kwargs) -> bool:
    """烈弓：使用杀时，若目标手牌数>=你体力值或<=你攻击范围，其不能闪避."""
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
    """狂骨：对距离1以内的角色造成伤害后回复1点体力."""
    if not target:
        return False

    distance = engine.calculate_distance(player, target)
    if distance <= 1 and player.hp < player.max_hp:
        player.heal(1)
        engine.log_event("skill", _t("skill_msg.kuanggu", name=player.name))
        return True
    return False


# ==================== 胡金定 ====================


@skill_handler("qingyuan")
def handle_qingyuan(
    player: Player,
    engine: GameEngine,
    mode: str = "mark",
    target: Player | None = None,
    marked_target: Player | None = None,
    stolen_card: Card | None = None,
    **kwargs,
) -> bool:
    """轻缘：起始/首伤时添加标记，标记角色获得牌后每回合限一次掠取其手牌."""
    state = player.get_skill_state("qingyuan")
    marked_ids = set(state.get("marked_player_ids", set()))

    if mode in {"mark", "mark_after_damage"}:
        candidates = [
            other for other in engine.get_other_players(player) if other.id not in marked_ids
        ]
        if target in candidates:
            chosen_target = target
        elif candidates:
            chosen_target = candidates[0]
        else:
            return False

        marked_ids.add(chosen_target.id)
        state["marked_player_ids"] = marked_ids
        if mode == "mark_after_damage":
            state["first_damage_marked"] = True
        engine.log_event(
            "skill", f"{player.name}发动【轻缘】，令{chosen_target.name}获得“轻缘”标记"
        )
        return True

    if mode != "trigger_obtain":
        return False

    turn_marker = (engine.round_count, engine.current_player.id)
    if state.get("last_trigger_turn") == turn_marker:
        return False

    candidates = [
        other
        for other in engine.players
        if other.is_alive and other.id in marked_ids and other != player and other.hand_count > 0
    ]
    if marked_target in candidates:
        chosen_target = marked_target
    elif candidates:
        chosen_target = random.choice(candidates)
    else:
        return False

    if stolen_card not in chosen_target.hand:
        stolen_card = random.choice(chosen_target.hand)

    chosen_target.remove_card(stolen_card)
    engine.notify_cards_lost(
        chosen_target,
        [stolen_card],
        source=player,
        to_player=player,
        reason="qingyuan",
    )
    player.draw_cards([stolen_card])
    engine.notify_cards_obtained(
        player,
        [stolen_card],
        source=player,
        from_player=chosen_target,
        reason="qingyuan",
    )
    state["last_trigger_turn"] = turn_marker
    engine.log_event("skill", f"{player.name}的【轻缘】触发，获得了{chosen_target.name}的一张手牌")
    return True


@skill_handler("zhongshen")
def handle_zhongshen(
    player: Player,
    engine: GameEngine,
    card: Card | None = None,
    **kwargs,
) -> bool:
    """重身：本轮获得的红色牌可当闪使用."""
    if card is None:
        return False
    zhongshen_state = player.get_skill_state("zhongshen")
    round_red_ids = set(zhongshen_state.get("round_red_card_ids", set()))
    return card in player.hand and card.is_red and card.id in round_red_ids


# ==================== 界法正 ====================


@skill_handler("xuanhuo")
def handle_xuanhuo(
    player: Player,
    engine: GameEngine,
    targets: list[Player] | None = None,
    cards: list[Card] | None = None,
    choice: str = "take",
    obtained_cards: list[Card] | None = None,
    sha_card: Card | None = None,
    **kwargs,
) -> bool:
    """眩惑：交两张牌给一名角色，再令其杀人或被你获取两张手牌."""
    from ..card import CardName

    if (not targets or len(targets) < 2 or not cards or len(cards) != 2) and player.is_ai:
        if player.hand_count < 2:
            return False

        remaining_cards = list(player.hand)
        chosen_cards = []
        for _ in range(2):
            chosen_card = pick_least_valuable(remaining_cards, player)
            chosen_cards.append(chosen_card)
            remaining_cards.remove(chosen_card)
        cards = chosen_cards

        friends = [other for other in get_friends(player, engine) if other.is_alive]
        enemies = [
            other
            for other in engine.get_other_players(player)
            if other.is_alive and is_enemy(player, other)
        ]

        sha_options = []
        for friend in friends:
            sha_cards = friend.get_cards_by_name(CardName.SHA)
            targets_in_range = [
                enemy
                for enemy in enemies
                if enemy != friend and engine.is_in_attack_range(friend, enemy)
            ]
            if sha_cards and targets_in_range:
                sha_options.append((friend, sha_cards[0], targets_in_range))

        if sha_options:
            receiver, sha_card, receiver_targets = max(
                sha_options,
                key=lambda option: (option[0].hand_count, -min(target.hp for target in option[2])),
            )
            forced_target = min(receiver_targets, key=lambda target: (target.hp, target.hand_count))
            targets = [receiver, forced_target]
            choice = "sha"
        else:
            receiver_candidates = [other for other in enemies if other.hand_count >= 2]
            if not receiver_candidates:
                return False

            receiver = max(receiver_candidates, key=lambda target: (target.hand_count, target.hp))
            forced_candidates = [
                other for other in engine.get_other_players(player) if other != receiver
            ]
            if not forced_candidates:
                return False
            preferred_targets = [other for other in enemies if other != receiver]
            forced_target = min(
                preferred_targets or forced_candidates,
                key=lambda target: (target.hp, target.hand_count),
            )
            targets = [receiver, forced_target]
            choice = "take"
            obtained_cards = list(receiver.hand[:2])

    if not targets or len(targets) < 2 or not cards or len(cards) != 2:
        return False

    receiver = targets[0]
    forced_target = targets[1]
    if player in (receiver, forced_target) or receiver == forced_target:
        return False
    if any(card not in player.hand for card in cards):
        return False

    if choice == "sha":
        candidate_sha = list(receiver.get_cards_by_name(CardName.SHA))
        candidate_sha.extend(card for card in cards if card.name == CardName.SHA)
        if not candidate_sha:
            return False

    player.remove_cards(cards)
    engine.notify_cards_lost(player, cards, source=player, to_player=receiver, reason="xuanhuo")
    receiver.draw_cards(cards)
    engine.notify_cards_obtained(
        receiver, cards, source=player, from_player=player, reason="xuanhuo"
    )
    engine.log_event("skill", f"{player.name}发动【眩惑】，交给{receiver.name}两张牌")

    if choice == "sha":
        if sha_card not in receiver.hand:
            sha_cards = receiver.get_cards_by_name(CardName.SHA)
            if not sha_cards:
                return False
            sha_card = sha_cards[0]
        return engine.use_card(receiver, sha_card, [forced_target])

    receiver_hand_cards = list(receiver.hand)
    if len(receiver_hand_cards) < 2:
        return False

    chosen_cards = list(obtained_cards or receiver_hand_cards[:2])[:2]
    if any(card not in receiver.hand for card in chosen_cards):
        return False

    receiver.remove_cards(chosen_cards)
    engine.notify_cards_lost(
        receiver,
        chosen_cards,
        source=player,
        to_player=player,
        reason="xuanhuo",
    )
    player.draw_cards(chosen_cards)
    engine.notify_cards_obtained(
        player,
        chosen_cards,
        source=player,
        from_player=receiver,
        reason="xuanhuo",
    )
    engine.log_event("skill", f"{player.name}发动【眩惑】，从{receiver.name}处获得两张手牌")
    return True


@skill_handler("enyuan")
def handle_enyuan(
    player: Player,
    engine: GameEngine,
    mode: str = "damage",
    source: Player | None = None,
    from_player: Player | None = None,
    red_card: Card | None = None,
    **kwargs,
) -> bool:
    """恩怨：获得两张牌后可令对方摸一，受伤后索红手牌或令来源失去体力."""
    if mode == "reward_source":
        if from_player is None or from_player == player:
            return False
        drawn_cards = engine.deck.draw(1)
        if drawn_cards:
            from_player.draw_cards(drawn_cards)
            engine.notify_cards_obtained(from_player, drawn_cards, source=player, reason="enyuan")
        engine.log_event("skill", f"{player.name}发动【恩怨】，令{from_player.name}摸一张牌")
        return True

    if mode != "damage" or source is None or source == player or not source.is_alive:
        return False

    red_hand_cards = [candidate for candidate in source.hand if candidate.is_red]
    if red_card in red_hand_cards:
        chosen_card = red_card
    elif red_hand_cards:
        chosen_card = red_hand_cards[0]
    else:
        chosen_card = None

    if chosen_card:
        source.remove_card(chosen_card)
        engine.notify_cards_lost(
            source,
            [chosen_card],
            source=source,
            to_player=player,
            reason="enyuan",
        )
        player.draw_cards([chosen_card])
        engine.notify_cards_obtained(
            player,
            [chosen_card],
            source=source,
            from_player=source,
            reason="enyuan",
        )
        engine.log_event("skill", f"{player.name}发动【恩怨】，获得了{source.name}的一张红色手牌")
        return True

    source.hp -= 1
    engine.log_event("skill", f"{player.name}发动【恩怨】，令{source.name}失去1点体力")
    if source.hp <= 0:
        source.is_dying = True
        engine._handle_dying(source)
    return True


# ==================== 向宠 ====================


def _recover_lost_card(engine: GameEngine, lost_card: Card) -> bool:
    """从弃牌堆或场上区域取回指定牌."""
    if lost_card in engine.deck.discard_pile:
        engine.deck.discard_pile.remove(lost_card)
        return True

    for holder in engine.players:
        if lost_card in holder.hand:
            holder.remove_card(lost_card)
            return True
        if holder.equipment.unequip_card(lost_card):
            return True
        if lost_card in holder.judge_area:
            holder.judge_area.remove(lost_card)
            return True
    return False


def _card_is_in_known_zone(engine: GameEngine, card: Card) -> bool:
    """检查卡牌当前是否已经落入已知区域."""
    if card in engine.deck.discard_pile:
        return True
    for holder in engine.players:
        if card in holder.hand:
            return True
        if card in holder.equipment.get_all_cards():
            return True
        if card in holder.judge_area:
            return True
    return False


@skill_handler("guying")
def handle_guying(
    player: Player,
    engine: GameEngine,
    mode: str = "lost_one_card",
    lost_card: Card | None = None,
    current_player: Player | None = None,
    choice: str | None = None,
    gift_card: Card | None = None,
    **kwargs,
) -> bool:
    """固营：其他角色回合内失一牌后索回或换牌，并在下个准备阶段弃牌."""
    from ..card import CardType

    state = player.get_skill_state("guying")

    if mode == "prepare_discard":
        pending_count = int(state.get("pending_prepare_discard", 0))
        if pending_count <= 0:
            return False
        state["pending_prepare_discard"] = max(0, pending_count - 1)
        if player.hand:
            engine.discard_cards(player, [player.hand[0]])
            engine.log_event("skill", f"{player.name}结算【固营】后续效果，弃置了一张牌")
        return True

    if mode != "lost_one_card" or lost_card is None or current_player is None:
        return False

    marker = (engine.round_count, current_player.id)
    used_turn_markers = set(state.get("used_turn_markers", set()))
    if marker in used_turn_markers:
        return False

    if choice is None:
        choice = "give" if current_player.hand else "return"

    if choice == "give":
        if gift_card not in current_player.hand:
            if not current_player.hand:
                return False
            gift_card = random.choice(current_player.hand)
        current_player.remove_card(gift_card)
        engine.notify_cards_lost(
            current_player,
            [gift_card],
            source=current_player,
            to_player=player,
            reason="guying",
        )
        player.draw_cards([gift_card])
        engine.notify_cards_obtained(
            player,
            [gift_card],
            source=current_player,
            from_player=current_player,
            reason="guying",
        )
        success = True
    else:
        success = _recover_lost_card(engine, lost_card)
        if not success and not _card_is_in_known_zone(engine, lost_card):
            success = True
        if not success:
            return False
        player.draw_cards([lost_card])
        engine.notify_cards_obtained(player, [lost_card], source=current_player, reason="guying")
        if lost_card.card_type == CardType.EQUIPMENT and lost_card in player.hand:
            engine.use_card(player, lost_card)

    used_turn_markers.add(marker)
    state["used_turn_markers"] = used_turn_markers
    state["pending_prepare_discard"] = int(state.get("pending_prepare_discard", 0)) + 1
    engine.log_event("skill", f"{player.name}发动【固营】，当前回合角色选择了“{choice}”")
    return success


@skill_handler("muzhen")
def handle_muzhen(
    player: Player,
    engine: GameEngine,
    targets: list[Player] | None = None,
    cards: list[Card] | None = None,
    option: int = 1,
    equip_card: Card | None = None,
    stolen_card: Card | None = None,
    **kwargs,
) -> bool:
    """睦阵：每项各限一次的两种换装换牌选项."""
    from ..card import CardSubtype, CardType

    state = player.get_skill_state("muzhen")
    if not targets:
        return False
    target = targets[0]
    if target == player:
        return False

    if option == 1:
        if state.get("option_one_used", False) or not cards or len(cards) != 2:
            return False
        if any(card not in player.hand for card in cards) or not target.equipment.has_equipment():
            return False

        player.remove_cards(cards)
        engine.notify_cards_lost(player, cards, source=player, to_player=target, reason="muzhen")
        target.draw_cards(cards)
        engine.notify_cards_obtained(
            target, cards, source=player, from_player=player, reason="muzhen"
        )

        target_equipment = target.equipment.get_all_cards()
        if not target_equipment:
            return False
        if equip_card not in target_equipment:
            equip_card = target_equipment[0]
        engine.equipment_sys.remove(
            target, equip_card, source=player, to_player=player, reason="muzhen"
        )
        player.draw_cards([equip_card])
        engine.notify_cards_obtained(
            player,
            [equip_card],
            source=player,
            from_player=target,
            reason="muzhen",
        )
        state["option_one_used"] = True
        engine.log_event("skill", f"{player.name}发动【睦阵】第一项，与{target.name}交换了牌与装备")
        return True

    if option != 2 or state.get("option_two_used", False) or not cards:
        return False

    equipment_cards = [
        card for card in cards if card.card_type == CardType.EQUIPMENT and card in player.hand
    ]
    if not equipment_cards or target.hand_count <= 0:
        return False
    equipment_card = equipment_cards[0]

    slot_name = {
        CardSubtype.WEAPON: "weapon",
        CardSubtype.ARMOR: "armor",
        CardSubtype.HORSE_MINUS: "horse_minus",
        CardSubtype.HORSE_PLUS: "horse_plus",
    }.get(equipment_card.subtype)
    if not slot_name or getattr(target.equipment, slot_name) is not None:
        return False

    player.remove_card(equipment_card)
    engine.notify_cards_lost(
        player,
        [equipment_card],
        source=player,
        to_player=target,
        reason="muzhen",
    )
    target.equip_card(equipment_card)
    engine.notify_cards_obtained(
        target,
        [equipment_card],
        source=player,
        from_player=player,
        reason="muzhen",
    )

    if stolen_card not in target.hand:
        stolen_card = target.hand[0]
    target.remove_card(stolen_card)
    engine.notify_cards_lost(
        target, [stolen_card], source=player, to_player=player, reason="muzhen"
    )
    player.draw_cards([stolen_card])
    engine.notify_cards_obtained(
        player,
        [stolen_card],
        source=player,
        from_player=target,
        reason="muzhen",
    )
    state["option_two_used"] = True
    engine.log_event(
        "skill", f"{player.name}发动【睦阵】第二项，将装备置入{target.name}装备区并获得其一张手牌"
    )
    return True


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
    "qingyuan": handle_qingyuan,
    "zhongshen": handle_zhongshen,
    "xuanhuo": handle_xuanhuo,
    "enyuan": handle_enyuan,
    "guying": handle_guying,
    "muzhen": handle_muzhen,
}
