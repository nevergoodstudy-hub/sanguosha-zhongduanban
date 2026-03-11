from ai.bot import AIBot, AIDifficulty
from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.constants import SkillId
from game.engine import GameEngine, GameState
from game.events import EventType
from game.player import Identity
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


def create_engine_with_ai(hero_ids: list[str], difficulty: AIDifficulty) -> GameEngine:
    engine = GameEngine()
    engine.setup_game(player_count=len(hero_ids), human_player_index=-1)
    skill_system = SkillSystem(engine)
    engine.set_skill_system(skill_system)
    engine.choose_heroes(dict(enumerate(hero_ids)))
    for player in engine.players:
        engine.ai_bots[player.id] = AIBot(player, difficulty)
    engine.start_game()
    assert engine.skill_system is not None
    return engine


def test_setup_headless_game_initializes_skill_system():
    engine = GameEngine()
    engine.setup_headless_game(4, seed=42)

    assert engine.state == GameState.IN_PROGRESS
    assert engine.skill_system is not None
    assert engine.round_count == 1
    assert engine.current_player.identity == Identity.LORD


def test_ai_xuanhuo_triggers_at_draw_phase_end_without_manual_targets():
    engine = create_engine_with_ai(["jiefazheng", "liubei", "caocao"], AIDifficulty.NORMAL)
    player, receiver, other_enemy = engine.players[:3]
    give_one = make_card("ai_xuanhuo_give_1", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL)
    give_two = make_card("ai_xuanhuo_give_2", name=CardName.SHAN, subtype=CardSubtype.DODGE)
    take_one = make_card("ai_xuanhuo_take_1", name=CardName.SHA, subtype=CardSubtype.ATTACK)
    take_two = make_card("ai_xuanhuo_take_2", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL)
    blocker = make_card("ai_xuanhuo_blocker", name=CardName.SHAN, subtype=CardSubtype.DODGE)

    player.hand = [give_one, give_two]
    receiver.hand = [take_one, take_two]
    other_enemy.hand = [blocker]

    engine.event_bus.emit(EventType.PHASE_DRAW_END, player=player)

    assert take_one in player.hand
    assert take_two in player.hand
    assert give_one not in player.hand
    assert give_two not in player.hand
    assert receiver.hand_count == 3


def test_normal_ai_uses_muzhen_when_target_has_equipment():
    engine = create_engine_with_ai(["xiangchong", "liubei"], AIDifficulty.NORMAL)
    player, target = engine.players[:2]
    gift_one = make_card("ai_muzhen_gift_1", name=CardName.TAO, suit=CardSuit.HEART, subtype=CardSubtype.HEAL)
    gift_two = make_card("ai_muzhen_gift_2", name=CardName.SHAN, subtype=CardSubtype.DODGE)
    target_weapon = make_card(
        "ai_muzhen_weapon",
        name=CardName.GUDINGDAO,
        card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.WEAPON,
        range=2,
    )

    player.hand = [gift_one, gift_two]
    target.hand.clear()
    target.equipment.weapon = target_weapon

    engine.ai_bots[player.id].play_phase(player, engine)

    state = player.get_skill_state(SkillId.MUZHEN)
    assert state["option_one_used"] is True
    assert target.equipment.weapon is None
    assert target.hand_count == 2
    assert gift_one in target.hand
    assert gift_two in target.hand


def test_normal_ai_uses_yanliang_for_qun_lord_when_attack_is_available():
    engine = create_engine_with_ai(["mouyuanshu", "jieliubiao", "liubei"], AIDifficulty.NORMAL)
    lord, donor, other_player = engine.players[:3]
    donor.identity = Identity.REBEL
    other_player.identity = Identity.LOYALIST
    support_equipment = make_card(
        "ai_yanliang_weapon",
        name=CardName.ZHUGENU,
        card_type=CardType.EQUIPMENT,
        subtype=CardSubtype.WEAPON,
    )
    sha_card = make_card("ai_yanliang_sha", name=CardName.SHA, subtype=CardSubtype.ATTACK)
    donor.hand = [support_equipment, sha_card]

    engine.ai_bots[donor.id].play_phase(donor, engine)

    assert donor.get_turn_flag("yanliang_used") is True
    assert donor.alcohol_used is True
    assert support_equipment in lord.hand


def test_headless_battle_finishes_with_all_synced_heroes_under_normal_and_hard_ai():
    hero_ids = ["mouyuanshu", "hujinding", "jieliubiao", "jiefazheng", "xiangchong"]
    for difficulty in (AIDifficulty.NORMAL, AIDifficulty.HARD):
        engine = create_engine_with_ai(hero_ids, difficulty)
        result = engine.run_headless_battle(max_rounds=40)
        assert result["rounds"] > 0
        assert result["heroes"] == ["谋袁术", "胡金定", "界刘表", "界法正", "向宠"]
