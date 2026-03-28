"""Tests for GameAction metadata serialization."""

from game.actions import EndPhaseAction
from game.engine import GameEngine


def test_serialize_action_includes_metadata_fields():
    engine = GameEngine()
    action = EndPhaseAction(
        player_id=1,
        source_channel="network",
        correlation_id="corr-123",
        action_id="act-999",
    )

    payload = engine._serialize_action(action)

    assert payload["type"] == "END_PHASE"
    assert payload["source_channel"] == "network"
    assert payload["correlation_id"] == "corr-123"
    assert payload["action_id"] == "act-999"
