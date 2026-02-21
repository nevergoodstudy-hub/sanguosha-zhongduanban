"""Game integration tests (P2-1).

Tests for combat, game over detection, distance calculation,
and damage/death flow using real GameEngine instances.
"""

import copy

import pytest

from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.engine import GameEngine
from game.enums import GamePhase, GameState
from game.player import Identity, Player


def _make_sha(suit: CardSuit = CardSuit.SPADE, number: int = 7) -> Card:
    return Card(
        id=f"test_sha_{suit.value}_{number}",
        name=CardName.SHA,
        card_type=CardType.BASIC,
        subtype=CardSubtype.ATTACK,
        suit=suit,
        number=number,
    )


def _make_shan(suit: CardSuit = CardSuit.DIAMOND, number: int = 2) -> Card:
    return Card(
        id=f"test_shan_{suit.value}_{number}",
        name=CardName.SHAN,
        card_type=CardType.BASIC,
        subtype=CardSubtype.DODGE,
        suit=suit,
        number=number,
    )


def _make_tao() -> Card:
    return Card(
        id="test_tao",
        name=CardName.TAO,
        card_type=CardType.BASIC,
        subtype=CardSubtype.HEAL,
        suit=CardSuit.HEART,
        number=3,
    )


def _setup_engine(player_count: int = 4) -> GameEngine:
    """Create a fully initialized engine with all AI players."""
    engine = GameEngine(data_dir="data")
    engine.setup_headless_game(player_count, seed=42)
    return engine


class TestGameOverDetection:
    """Test check_game_over() under various conditions."""

    def test_game_not_over_initially(self):
        engine = _setup_engine(4)
        assert engine.check_game_over() is False
        assert engine.state == GameState.IN_PROGRESS

    def test_lord_dies_rebel_wins(self):
        engine = _setup_engine(4)
        lord = None
        for p in engine.players:
            if p.identity == Identity.LORD:
                lord = p
                break
        assert lord is not None
        # Kill the lord
        lord.die()
        result = engine.check_game_over()
        assert result is True
        assert engine.state == GameState.FINISHED
        # Should be REBEL or SPY win depending on remaining
        assert engine.winner_identity in (Identity.REBEL, Identity.SPY)

    def test_all_rebels_and_spies_dead_lord_wins(self):
        engine = _setup_engine(4)
        for p in engine.players:
            if p.identity in (Identity.REBEL, Identity.SPY):
                p.die()
        result = engine.check_game_over()
        assert result is True
        assert engine.winner_identity == Identity.LORD

    def test_only_spy_alive_after_lord_dies(self):
        """If lord dies and only spy remains, spy wins."""
        engine = _setup_engine(4)
        # Kill everyone except the spy
        spy = None
        for p in engine.players:
            if p.identity == Identity.SPY:
                spy = p
            else:
                p.die()
        if spy is None:
            pytest.skip("No spy in 4-player game with this seed")
        result = engine.check_game_over()
        assert result is True
        assert engine.winner_identity == Identity.SPY


class TestDamageFlow:
    """Test deal_damage and death handling."""

    def test_deal_damage_reduces_hp(self):
        engine = _setup_engine(2)
        attacker = engine.players[0]
        target = engine.players[1]
        old_hp = target.hp
        engine.deal_damage(attacker, target, 1)
        assert target.hp == old_hp - 1

    def test_deal_damage_zero_ignored(self):
        engine = _setup_engine(2)
        target = engine.players[1]
        old_hp = target.hp
        engine.deal_damage(engine.players[0], target, 0)
        assert target.hp == old_hp  # no change

    def test_deal_damage_dead_target_ignored(self):
        engine = _setup_engine(2)
        target = engine.players[1]
        target.die()
        # Should not crash
        engine.deal_damage(engine.players[0], target, 1)


class TestDistanceCalculation:
    """Test calculate_distance with horse modifiers."""

    def test_distance_to_self_is_zero(self):
        engine = _setup_engine(4)
        p = engine.players[0]
        assert engine.calculate_distance(p, p) == 0

    def test_distance_symmetric_without_horses(self):
        engine = _setup_engine(4)
        p0 = engine.players[0]
        p1 = engine.players[1]
        # Without equipment modifiers, distance should be same both ways
        d01 = engine.calculate_distance(p0, p1)
        d10 = engine.calculate_distance(p1, p0)
        assert d01 == d10

    def test_distance_minimum_is_one(self):
        """Distance between different players is at least 1."""
        engine = _setup_engine(4)
        for i in range(len(engine.players)):
            for j in range(len(engine.players)):
                if i != j:
                    d = engine.calculate_distance(engine.players[i], engine.players[j])
                    assert d >= 1

    def test_distance_4_players_adjacent_is_1(self):
        engine = _setup_engine(4)
        # In a 4-player game, adjacent players are distance 1
        d = engine.calculate_distance(engine.players[0], engine.players[1])
        assert d == 1

    def test_distance_4_players_opposite_is_2(self):
        engine = _setup_engine(4)
        # In a 4-player game, opposite players are distance 2
        d = engine.calculate_distance(engine.players[0], engine.players[2])
        assert d == 2

    def test_attack_range_check(self):
        engine = _setup_engine(4)
        p0 = engine.players[0]
        p1 = engine.players[1]
        # Default attack range is 1, adjacent is 1
        assert engine.is_in_attack_range(p0, p1) is True

    def test_targets_in_range(self):
        engine = _setup_engine(4)
        targets = engine.get_targets_in_range(engine.players[0])
        # Default weapon range 1 → only adjacent players
        assert len(targets) >= 1
        assert engine.players[0] not in targets


class TestTurnFlow:
    """Test basic turn progression."""

    def test_next_turn_advances_player(self):
        engine = _setup_engine(4)
        initial_idx = engine.current_player_index
        engine.next_turn()
        assert engine.current_player_index != initial_idx

    def test_next_turn_skips_dead_player(self):
        engine = _setup_engine(4)
        engine.current_player_index = 0
        engine.players[1].die()
        engine.next_turn()
        # Should skip player 1
        assert engine.current_player_index != 1

    def test_round_count_increments(self):
        engine = _setup_engine(4)
        initial_round = engine.round_count
        # Cycle through all players
        for _ in range(len(engine.players)):
            engine.next_turn()
        assert engine.round_count > initial_round


class TestCombatSha:
    """Test SHA (attack) card usage through combat system."""

    def test_sha_with_no_shan_deals_damage(self):
        engine = _setup_engine(2)
        attacker = engine.players[0]
        target = engine.players[1]
        engine.current_player_index = 0

        # Clear target hand so they can't respond
        target.hand.clear()
        sha = _make_sha()
        attacker.draw_cards([sha])
        old_hp = target.hp

        engine.combat.use_sha(attacker, sha, [target])
        assert target.hp < old_hp

    def test_sha_requires_attack_range(self):
        engine = _setup_engine(4)
        attacker = engine.players[0]
        # Pick a target out of range (opposite in 4-player game)
        target = engine.players[2]  # distance 2, range 1
        sha = _make_sha()
        attacker.draw_cards([sha])
        old_hp = target.hp

        engine.combat.use_sha(attacker, sha, [target])
        # Target should NOT take damage (out of range)
        assert target.hp == old_hp
