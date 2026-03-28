"""Tests for room-driven engine setup."""

from game.engine import GameEngine
from game.enums import GameState


def test_setup_room_game_preserves_connected_player_ids_and_names():
    engine = GameEngine()

    engine.setup_room_game(
        connected_players=[(101, "Host"), (205, "Guest")],
        total_player_count=4,
        seed=1234,
    )

    human_players = [player for player in engine.players if not player.is_ai]
    ai_players = [player for player in engine.players if player.is_ai]

    assert [player.id for player in human_players] == [101, 205]
    assert [player.name for player in human_players] == ["Host", "Guest"]
    assert len(ai_players) == 2
    assert engine.state == GameState.IN_PROGRESS
    assert engine.current_player.id == engine.lord_player.id
    assert all(player.hero is not None for player in engine.players)


def test_setup_room_game_without_ai_fill_keeps_exact_player_count():
    engine = GameEngine()

    engine.setup_room_game(
        connected_players=[(7, "A"), (8, "B"), (9, "C")],
        total_player_count=3,
        seed=42,
    )

    assert len(engine.players) == 3
    assert all(not player.is_ai for player in engine.players)
