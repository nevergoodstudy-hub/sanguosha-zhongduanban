"""Tests for net.action_codec."""

import pytest

from game.actions import DiscardAction, EndPhaseAction, PlayCardAction, UseSkillAction
from net.action_codec import decode_client_action


def test_decode_play_card_action_uses_string_card_id():
    action = decode_client_action(
        1,
        {"action_type": "play_card", "card_id": "sha_spade_A", "target_ids": [2, 3]},
    )

    assert isinstance(action, PlayCardAction)
    assert action.player_id == 1
    assert action.card_id == "sha_spade_A"
    assert action.target_ids == [2, 3]


def test_decode_use_skill_action_supports_string_card_ids():
    action = decode_client_action(
        9,
        {
            "action_type": "use_skill",
            "skill_id": "wusheng",
            "target_ids": [1],
            "card_ids": ["sha_spade_A"],
        },
    )

    assert isinstance(action, UseSkillAction)
    assert action.card_ids == ["sha_spade_A"]


def test_decode_use_skill_action_supports_extra_payload():
    action = decode_client_action(
        9,
        {
            "action_type": "use_skill",
            "skill_id": "muzhen",
            "target_ids": [1],
            "extra_payload": {"option": 2, "stolen_card": "sha_spade_A"},
        },
    )

    assert isinstance(action, UseSkillAction)
    assert action.extra_payload["option"] == 2


def test_decode_discard_action_supports_string_card_ids():
    action = decode_client_action(
        3,
        {"action_type": "discard", "card_ids": ["sha_spade_A", "shan_heart_2"]},
    )

    assert isinstance(action, DiscardAction)
    assert action.card_ids == ["sha_spade_A", "shan_heart_2"]


def test_decode_end_turn_action():
    action = decode_client_action(4, {"action_type": "end_turn"})
    assert isinstance(action, EndPhaseAction)
    assert action.player_id == 4


def test_decode_play_card_rejects_non_string_card_id():
    with pytest.raises(ValueError, match="card_id"):
        decode_client_action(1, {"action_type": "play_card", "card_id": 42})


def test_decode_action_includes_source_channel_and_correlation_id():
    action = decode_client_action(
        11,
        {
            "action_type": "end_turn",
            "source_channel": "network",
            "correlation_id": "turn-11-abc",
            "action_id": "act-custom-1",
        },
    )

    assert isinstance(action, EndPhaseAction)
    assert action.source_channel == "network"
    assert action.correlation_id == "turn-11-abc"
    assert action.action_id == "act-custom-1"


def test_decode_action_falls_back_to_default_metadata_when_invalid():
    action = decode_client_action(
        5,
        {
            "action_type": "end_turn",
            "source_channel": "",
            "correlation_id": "   ",
            "action_id": "   ",
        },
    )

    assert isinstance(action, EndPhaseAction)
    assert action.source_channel == "network"
    assert action.correlation_id is None
    assert isinstance(action.action_id, str)
    assert action.action_id
