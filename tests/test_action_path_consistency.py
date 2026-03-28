"""动作路径一致性测试：UI / AI / 网络三路径."""

from __future__ import annotations

from unittest.mock import MagicMock

from ai.strategy import execute_use_skill_action
from game.actions import PlayCardAction, UseSkillAction
from game.engine import GameEngine
from net.action_codec import decode_client_action


def test_ai_skill_action_uses_execute_action_with_extra_payload() -> None:
    engine = MagicMock()
    engine.execute_action.return_value = True

    player = MagicMock()
    player.id = 7

    target = MagicMock()
    target.id = 2

    card = MagicMock()
    card.id = "card-1"

    result = execute_use_skill_action(
        engine,
        "muzhen",
        player,
        targets=[target],
        cards=[card],
        option=2,
        stolen_card="dummy",
    )

    assert result is True
    engine.execute_action.assert_called_once()
    action = engine.execute_action.call_args.args[0]

    assert isinstance(action, UseSkillAction)
    assert action.source_channel == "ai"
    assert action.target_ids == [2]
    assert action.card_ids == ["card-1"]
    assert action.extra_payload == {"option": 2, "stolen_card": "dummy"}


def test_network_action_decode_keeps_network_channel_and_payload() -> None:
    action = decode_client_action(
        3,
        {
            "action_type": "use_skill",
            "skill_id": "muzhen",
            "target_ids": [8],
            "card_ids": ["card-9"],
            "source_channel": "network",
            "extra_payload": {"option": 1},
        },
    )

    assert isinstance(action, UseSkillAction)
    assert action.source_channel == "network"
    assert action.extra_payload == {"option": 1}


def test_ui_action_serialization_keeps_channel_metadata() -> None:
    engine = GameEngine()
    action = PlayCardAction(
        player_id=1,
        card_id="sha-1",
        target_ids=[2],
        source_channel="textual_ui",
        correlation_id="ui-turn-1",
    )

    payload = engine._serialize_action(action)

    assert payload["source_channel"] == "textual_ui"
    assert payload["correlation_id"] == "ui-turn-1"
