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
