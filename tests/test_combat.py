"""Tests for game/combat.py — CombatSystem unit tests."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.combat import CombatSystem


def _make_card(name=CardName.SHA, subtype=CardSubtype.ATTACK, suit=CardSuit.SPADE, number=7):  # noqa: D103
    return Card(
        id=f"test_{name}_{suit.value}_{number}",
        name=name,
        card_type=CardType.BASIC,
        subtype=subtype,
        suit=suit,
        number=number,
    )


def _mock_player(name="P1", hp=4, max_hp=4, hand_count=4, has_skills=None):
    p = MagicMock()
    p.name = name
    p.hp = hp
    p.max_hp = max_hp
    p.hand_count = hand_count
    p.is_ai = True
    p.has_skill = MagicMock(side_effect=lambda s: s in (has_skills or []))
    p.can_use_sha = MagicMock(return_value=True)
    p.use_sha = MagicMock()
    p.consume_drunk = MagicMock(return_value=False)
    p.remove_card = MagicMock()
    p.draw_cards = MagicMock()
    p.get_cards_by_name = MagicMock(return_value=[])
    p.get_red_cards = MagicMock(return_value=[])

    equip = MagicMock()
    equip.weapon = None
    equip.armor = None
    p.equipment = equip
    return p


def _mock_context():
    ctx = MagicMock()
    ctx.deck = MagicMock()
    ctx.deck.discard = MagicMock()
    ctx.is_in_attack_range = MagicMock(return_value=True)
    ctx.calculate_distance = MagicMock(return_value=1)
    ctx.log_event = MagicMock()
    ctx.deal_damage = MagicMock()
    ctx.request_handler = MagicMock()
    ctx.request_handler.request_shan = MagicMock(return_value=None)
    return ctx


# ==================== CombatSystem.use_sha ====================


class TestUseSha:
    def test_sha_hits_when_no_shan(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player("Attacker")
        target = _mock_player("Defender")
        card = _make_card()

        combat.use_sha(player, card, [target])

        player.use_sha.assert_called_once()
        ctx.deal_damage.assert_called_once_with(player, target, 1, "normal")
        ctx.deck.discard.assert_called_once_with([card])

    def test_sha_dodge_when_shan_provided(self):
        ctx = _mock_context()
        shan_card = _make_card(CardName.SHAN, CardSubtype.DODGE)
        ctx.request_handler.request_shan.return_value = shan_card
        combat = CombatSystem(ctx)
        player = _mock_player("Attacker")
        target = _mock_player("Defender")
        card = _make_card()

        combat.use_sha(player, card, [target])

        player.use_sha.assert_called_once()
        ctx.deal_damage.assert_not_called()

    def test_sha_no_targets_returns_false(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player()
        card = _make_card()

        result = combat.use_sha(player, card, [])
        assert result is False
        ctx.deck.discard.assert_called_once_with([card])

    def test_sha_out_of_range(self):
        ctx = _mock_context()
        ctx.is_in_attack_range.return_value = False
        combat = CombatSystem(ctx)
        player = _mock_player()
        player.can_use_sha.return_value = True
        target = _mock_player("Far")
        card = _make_card()

        result = combat.use_sha(player, card, [target])
        assert result is False

    def test_sha_limit_exceeded(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player()
        player.can_use_sha.return_value = False
        target = _mock_player()
        card = _make_card()

        result = combat.use_sha(player, card, [target])
        assert result is False

    def test_fire_sha_damage_type(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player()
        target = _mock_player()
        card = _make_card(subtype=CardSubtype.FIRE_ATTACK)

        combat.use_sha(player, card, [target])
        ctx.deal_damage.assert_called_once_with(player, target, 1, "fire")

    def test_thunder_sha_damage_type(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player()
        target = _mock_player()
        card = _make_card(subtype=CardSubtype.THUNDER_ATTACK)

        combat.use_sha(player, card, [target])
        ctx.deal_damage.assert_called_once_with(player, target, 1, "thunder")

    def test_drunk_bonus_damage(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player()
        player.consume_drunk.return_value = True
        target = _mock_player()
        card = _make_card()

        combat.use_sha(player, card, [target])
        ctx.deal_damage.assert_called_once_with(player, target, 2, "normal")

    def test_kongcheng_blocks_sha(self):
        ctx = _mock_context()
        combat = CombatSystem(ctx)
        player = _mock_player()
        target = _mock_player(hand_count=0, has_skills=["kongcheng"])
        card = _make_card()

        result = combat.use_sha(player, card, [target])
        assert result is False
        ctx.deal_damage.assert_not_called()


# ==================== CombatSystem.request_shan ====================


class TestRequestShan:
    def test_no_shan_returns_zero(self):
        ctx = _mock_context()
        ctx.request_handler.request_shan.return_value = None
        combat = CombatSystem(ctx)
        player = _mock_player()

        result = combat.request_shan(player, count=1)
        assert result == 0

    def test_shan_played_returns_one(self):
        ctx = _mock_context()
        shan = _make_card(CardName.SHAN, CardSubtype.DODGE)
        ctx.request_handler.request_shan.return_value = shan
        combat = CombatSystem(ctx)
        player = _mock_player()

        result = combat.request_shan(player, count=1)
        assert result == 1
        player.remove_card.assert_called_once_with(shan)


# ==================== CombatSystem.request_sha ====================


class TestRequestSha:
    def test_no_sha_returns_zero(self):
        ctx = _mock_context()
        ctx.request_handler.request_sha.return_value = None
        combat = CombatSystem(ctx)
        player = _mock_player()

        result = combat.request_sha(player, count=1)
        assert result == 0

    def test_sha_played_returns_one(self):
        ctx = _mock_context()
        sha = _make_card(CardName.SHA)
        ctx.request_handler.request_sha.return_value = sha
        combat = CombatSystem(ctx)
        player = _mock_player()

        result = combat.request_sha(player, count=1)
        assert result == 1
        player.remove_card.assert_called_once_with(sha)
