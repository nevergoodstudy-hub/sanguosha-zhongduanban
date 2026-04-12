import copy

from game.engine import GameEngine
from game.events import EventType
from game.player import Player


def test_player_skill_state_helpers_support_turn_and_round_resets():
    player = Player(id=1, name="tester")

    jinming_state = player.get_skill_state("jinming")
    jinming_state["current_option"] = 3
    jinming_state["deleted_options"] = {1}
    player.set_turn_flag("jinming_condition_met", True)
    player.set_round_flag("zhongshen_red_enabled", True)

    player.reset_turn()

    assert player.get_skill_state("jinming")["deleted_options"] == {1}
    assert player.get_turn_flag("jinming_condition_met") is False
    assert player.get_round_flag("zhongshen_red_enabled") is True

    player.reset_round()

    assert player.get_round_flag("zhongshen_red_enabled") is False
    assert player.get_skill_state("jinming")["deleted_options"] == {1}


def _started_engine() -> GameEngine:
    engine = GameEngine()
    engine.setup_game(player_count=2, human_player_index=-1)
    heroes = engine.hero_repo.get_all_heroes()[:2]
    choices = {0: heroes[0].id, 1: heroes[1].id}
    engine.choose_heroes(choices)
    engine.start_game()
    return engine


def test_deal_damage_emits_damage_inflicting_before_applying_damage():
    engine = _started_engine()
    source = engine.players[0]
    target = engine.players[1]
    starting_hp = target.hp

    def prevent_damage(event):
        event.prevent()

    engine.event_bus.subscribe(EventType.DAMAGE_INFLICTING, prevent_damage, priority=10)

    engine.deal_damage(source, target, 1)

    assert target.hp == starting_hp


def test_deal_damage_allows_damage_inflicting_handlers_to_modify_damage():
    engine = _started_engine()
    source = engine.players[0]
    target = engine.players[1]
    starting_hp = target.hp

    def increase_damage(event):
        event.modify_damage(2)

    engine.event_bus.subscribe(EventType.DAMAGE_INFLICTING, increase_damage, priority=10)

    engine.deal_damage(source, target, 1)

    assert target.hp == starting_hp - 2


def test_next_turn_wrap_resets_round_flags_and_emits_round_lifecycle_events():
    engine = _started_engine()
    lord = engine.players[engine.lord_player_index]

    for player in engine.players:
        player.set_round_flag("zhongshen_red_enabled", True)

    rounds = []

    def record_round_end(event):
        rounds.append((event.event_type, event.data["round"]))

    def record_round_start(event):
        rounds.append((event.event_type, event.data["round"]))

    engine.event_bus.subscribe(EventType.ROUND_END, record_round_end)
    engine.event_bus.subscribe(EventType.ROUND_START, record_round_start)

    engine.current_player_index = 1 if engine.lord_player_index == 0 else 0
    engine.next_turn()

    assert engine.current_player == lord
    assert engine.round_count == 2
    assert all(player.get_round_flag("zhongshen_red_enabled") is False for player in engine.players)
    assert rounds == [
        (EventType.ROUND_END, 1),
        (EventType.ROUND_START, 2),
    ]


def test_discard_cards_emits_card_lost_with_cards_and_reason():
    engine = _started_engine()
    player = engine.players[0]
    discarded = player.hand[0]
    events = []

    engine.event_bus.subscribe(EventType.CARD_LOST, lambda event: events.append(event))

    engine.discard_cards(player, [discarded])

    assert len(events) == 1
    assert events[0].player == player
    assert events[0].cards == [discarded]
    assert events[0].data["reason"] == "discard"


def test_choose_and_steal_card_emits_loss_and_obtain_events():
    engine = _started_engine()
    thief = engine.players[0]
    target = engine.players[1]
    target.hand = [copy.deepcopy(target.hand[0])]
    expected = target.hand[0]
    lost_events = []
    obtained_events = []

    engine.event_bus.subscribe(EventType.CARD_LOST, lambda event: lost_events.append(event))
    engine.event_bus.subscribe(EventType.CARD_OBTAINED, lambda event: obtained_events.append(event))

    stolen = engine.card_resolver.choose_and_steal_card(thief, target)

    assert stolen == expected
    assert len(lost_events) == 1
    assert len(obtained_events) == 1
    assert lost_events[0].player == target
    assert lost_events[0].cards == [expected]
    assert lost_events[0].data["reason"] == "steal"
    assert lost_events[0].data["to_player"] == thief
    assert obtained_events[0].player == thief
    assert obtained_events[0].cards == [expected]
    assert obtained_events[0].data["reason"] == "steal"
    assert obtained_events[0].data["from_player"] == target
