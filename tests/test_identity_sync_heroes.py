from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.constants import SkillId
from game.engine import GameEngine, GamePhase
from game.events import EventType
from game.skill import SkillSystem


def make_card(
    card_id: str,
    name: str = CardName.SHA,
    *,
    suit: CardSuit = CardSuit.SPADE,
    number: int = 1,
    card_type: CardType = CardType.BASIC,
    subtype: CardSubtype = CardSubtype.ATTACK,
    range: int = 1,
) -> Card:
    return Card(
        id=card_id,
        name=name,
        card_type=card_type,
        subtype=subtype,
        suit=suit,
        number=number,
        range=range,
    )


def create_engine(hero_ids: list[str]) -> GameEngine:
    engine = GameEngine()
    engine.setup_game(player_count=len(hero_ids), human_player_index=-1)
    skill_system = SkillSystem(engine)
    engine.set_skill_system(skill_system)
    engine.choose_heroes(dict(enumerate(hero_ids)))
    engine.start_game()
    assert engine.skill_system is not None
    return engine


def test_synced_heroes_load_with_expected_skill_ids():
    repo = GameEngine().hero_repo
    expected = {
        "mouyuanshu": [SkillId.JINMING, SkillId.XIAOSHI, SkillId.YANLIANG],
        "hujinding": [SkillId.QINGYUAN, SkillId.ZHONGSHEN],
        "jieliubiao": [SkillId.ZISHOU, SkillId.ZONGSHI],
        "jiefazheng": [SkillId.XUANHUO, SkillId.ENYUAN],
        "xiangchong": [SkillId.GUYING, SkillId.MUZHEN],
    }

    for hero_id, skill_ids in expected.items():
        hero = repo.get_hero(hero_id)
        assert hero is not None
        assert [skill.id for skill in hero.skills] == skill_ids


def test_jinming_resolve_supports_success_and_failure_paths():
    engine = create_engine(["mouyuanshu", "liubei"])
    player = engine.players[0]
    player.hand.clear()
    engine.deck.draw_pile = [
        make_card(
            f"jinming_draw_{index}", name=CardName.TAO, subtype=CardSubtype.HEAL, number=index + 1
        )
        for index in range(5)
    ]

    state = player.get_skill_state(SkillId.JINMING)
    assert engine.skill_system.trigger_skill(
        SkillId.JINMING, player, engine, mode="choose", option=1
    )
    player.set_turn_flag("recovered_hp_amount", 1)
    hp_before_success = player.hp
    assert engine.skill_system.trigger_skill(SkillId.JINMING, player, engine, mode="resolve")
    assert player.hand_count == 1
    assert player.hp == hp_before_success
    assert state.get("deleted_options", set()) == set()

    assert engine.skill_system.trigger_skill(
        SkillId.JINMING, player, engine, mode="choose", option=4
    )
    hp_before_failure = player.hp
    assert engine.skill_system.trigger_skill(SkillId.JINMING, player, engine, mode="resolve")
    assert player.hand_count == 5
    assert player.hp == hp_before_failure - 1
    assert 4 in state["deleted_options"]


def test_xiaoshi_adds_extra_target_and_draws_for_matching_attack_range():
    engine = create_engine(["mouyuanshu", "liubei", "simayi"])
    player, original_target, extra_target = engine.players[:3]
    player.hand = [make_card("xiaoshi_sha", name=CardName.SHA, subtype=CardSubtype.ATTACK)]
    player.get_skill_state(SkillId.JINMING)["current_option"] = 2
    extra_target.equipment.weapon = make_card(
        "xiaoshi_weapon",
        name=CardName.GUDINGDAO,
        card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.WEAPON,
        range=2,
    )
    targets = [original_target]
    hand_before = extra_target.hand_count

    engine.phase = GamePhase.PLAY
    assert engine.use_card(player, player.hand[0], targets)
    assert extra_target in targets
    assert extra_target.hand_count == hand_before + 2
    assert player.get_turn_flag("xiaoshi_used") is True


def test_yanliang_allows_qun_ally_to_give_equipment_and_use_jiu():
    engine = create_engine(["mouyuanshu", "huatuo", "liubei"])
    lord = engine.players[0]
    donor = engine.players[1]
    equipment = make_card(
        "yanliang_weapon",
        name=CardName.ZHUGENU,
        card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.WEAPON,
    )
    donor.hand = [equipment]

    assert engine.skill_system.trigger_skill(
        SkillId.YANLIANG,
        lord,
        engine,
        donor=donor,
        card=equipment,
    )
    assert equipment in lord.hand
    assert equipment not in donor.hand
    assert donor.alcohol_used is True
    assert donor.is_drunk is True
    assert donor.get_turn_flag("yanliang_used") is True


def test_qingyuan_marks_at_game_start_and_steals_when_marked_target_gains_cards():
    engine = create_engine(["hujinding", "liubei", "caocao"])
    player = engine.players[0]
    state = player.get_skill_state(SkillId.QINGYUAN)
    marked_ids = state["marked_player_ids"]
    assert len(marked_ids) == 1

    marked_target = next(
        candidate for candidate in engine.players[1:] if candidate.id in marked_ids
    )
    marked_target.hand.clear()
    gained_card = make_card(
        "qingyuan_gain", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL
    )
    marked_target.draw_cards([gained_card])
    engine.current_player_index = engine.players.index(marked_target)
    hand_before = player.hand_count

    engine.notify_cards_obtained(
        marked_target, [gained_card], source=marked_target, reason="test_gain"
    )

    assert player.hand_count == hand_before + 1
    assert marked_target.hand_count == 0
    assert state["last_trigger_turn"] == (engine.round_count, marked_target.id)


def test_zhongshen_lets_recently_obtained_red_card_be_used_as_shan():
    engine = create_engine(["hujinding", "liubei"])
    player = engine.players[0]
    player.hand.clear()
    red_card = make_card(
        "zhongshen_red",
        name=CardName.TAO,
        suit=CardSuit.HEART,
        number=7,
        subtype=CardSubtype.HEAL,
    )
    player.draw_cards([red_card])
    engine.notify_cards_obtained(player, [red_card], reason="test_red_gain")

    assert engine.combat.request_shan(player, 1) == 1
    assert red_card not in player.hand
    assert red_card in engine.deck.discard_pile


def test_zishou_draws_extra_cards_and_discards_them_after_dealing_damage():
    engine = create_engine(["jieliubiao", "liubei", "sunquan"])
    player = engine.players[0]
    player.hand.clear()
    engine.deck.draw_pile = [
        make_card(
            f"zishou_draw_{index}", name=CardName.TAO, subtype=CardSubtype.HEAL, number=index + 1
        )
        for index in range(5)
    ]

    engine.phase_draw(player)
    assert player.hand_count == 5
    assert player.get_turn_flag("zishou_used") is True
    assert player.get_turn_flag("zishou_draw_count") == 3

    player.set_turn_flag("zishou_damaged_others", True)
    hand_before_end = player.hand_count
    engine.event_bus.emit(EventType.PHASE_END_START, player=player)
    assert player.hand_count == hand_before_end - 3


def test_zongshi_increases_hand_limit_and_prevents_first_damage_per_kingdom():
    engine = create_engine(["jieliubiao", "liubei", "sunquan"])
    target, shu_source, wu_source = engine.players[:3]
    expected_hand_limit = target.hp + 3
    assert target.hand_limit == expected_hand_limit

    start_hp = target.hp
    shu_hand_before = shu_source.hand_count
    engine.deal_damage(shu_source, target, 1)
    assert target.hp == start_hp
    assert shu_source.hand_count == shu_hand_before + 1

    engine.deal_damage(shu_source, target, 1)
    assert target.hp == start_hp - 1

    wu_hand_before = wu_source.hand_count
    engine.deal_damage(wu_source, target, 1)
    assert target.hp == start_hp - 1
    assert wu_source.hand_count == wu_hand_before + 1


def test_xuanhuo_take_branch_transfers_two_cards_each_way():
    engine = create_engine(["jiefazheng", "liubei", "caocao"])
    player, receiver, forced_target = engine.players[:3]
    give_one = make_card(
        "xuanhuo_give_1", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL
    )
    give_two = make_card(
        "xuanhuo_give_2", name=CardName.SHAN, suit=CardSuit.DIAMOND, subtype=CardSubtype.DODGE
    )
    take_one = make_card("xuanhuo_take_1", name=CardName.SHA, subtype=CardSubtype.ATTACK)
    take_two = make_card(
        "xuanhuo_take_2", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL
    )
    player.hand = [give_one, give_two]
    receiver.hand = [take_one, take_two]

    assert engine.skill_system.trigger_skill(
        SkillId.XUANHUO,
        player,
        engine,
        targets=[receiver, forced_target],
        cards=[give_one, give_two],
        choice="take",
        obtained_cards=[take_one, take_two],
    )
    assert player.hand == [take_one, take_two]
    assert give_one in receiver.hand
    assert give_two in receiver.hand
    assert receiver.hand_count == 3


def test_enyuan_rewards_large_obtain_and_punishes_damage_source_without_red_cards():
    engine = create_engine(["jiefazheng", "liubei"])
    player, source = engine.players[:2]
    player.hand.clear()
    obtained_cards = [
        make_card(
            "enyuan_obtain_1", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL
        ),
        make_card("enyuan_obtain_2", name=CardName.SHAN, subtype=CardSubtype.DODGE),
    ]

    source_hand_before = source.hand_count
    player.draw_cards(obtained_cards)
    engine.notify_cards_obtained(
        player,
        obtained_cards,
        source=source,
        from_player=source,
        reason="test_enyuan_obtain",
    )
    assert source.hand_count == source_hand_before + 1

    source.hand.clear()
    source_hp_before = source.hp
    engine.deal_damage(source, player, 1)
    assert source.hp == source_hp_before - 1


def test_guying_triggers_on_single_card_loss_and_resolves_prepare_discard():
    engine = create_engine(["xiangchong", "liubei"])
    player = engine.players[0]
    current_player = engine.players[1]
    lost_card = make_card("guying_lost", name=CardName.SHAN, subtype=CardSubtype.DODGE)
    gift_card = make_card(
        "guying_gift", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL
    )
    player.hand = [lost_card]
    current_player.hand = [gift_card]
    engine.current_player_index = 1

    engine.discard_cards(player, [lost_card])

    state = player.get_skill_state(SkillId.GUYING)
    assert gift_card in player.hand
    assert gift_card not in current_player.hand
    assert state["pending_prepare_discard"] == 1

    hand_before_prepare = player.hand_count
    engine.event_bus.emit(EventType.PHASE_PREPARE_START, player=player)
    assert player.hand_count == hand_before_prepare - 1
    assert state["pending_prepare_discard"] == 0


def test_muzhen_supports_both_options_once_each():
    engine = create_engine(["xiangchong", "liubei", "caocao"])
    player, target_one, target_two = engine.players[:3]
    give_one = make_card(
        "muzhen_give_1", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL
    )
    give_two = make_card("muzhen_give_2", name=CardName.SHAN, subtype=CardSubtype.DODGE)
    placed_armor = make_card(
        "muzhen_armor",
        name=CardName.BAGUA,
        card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.ARMOR,
    )
    stolen_weapon = make_card(
        "muzhen_weapon",
        name=CardName.GUDINGDAO,
        card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.WEAPON,
        range=2,
    )
    stolen_hand_card = make_card("muzhen_take", name=CardName.SHA, subtype=CardSubtype.ATTACK)

    player.hand = [give_one, give_two, placed_armor]
    target_one.hand.clear()
    target_one.equipment.weapon = stolen_weapon
    target_two.hand = [stolen_hand_card]

    assert engine.skill_system.use_skill(
        SkillId.MUZHEN,
        player,
        targets=[target_one],
        cards=[give_one, give_two],
        option=1,
        equip_card=stolen_weapon,
    )
    assert stolen_weapon in player.hand
    assert target_one.equipment.weapon is None
    assert target_one.hand == [give_one, give_two]

    assert engine.skill_system.use_skill(
        SkillId.MUZHEN,
        player,
        targets=[target_two],
        cards=[placed_armor],
        option=2,
        stolen_card=stolen_hand_card,
    )
    state = player.get_skill_state(SkillId.MUZHEN)
    assert target_two.equipment.armor == placed_armor
    assert stolen_hand_card in player.hand
    assert state["option_one_used"] is True
    assert state["option_two_used"] is True
