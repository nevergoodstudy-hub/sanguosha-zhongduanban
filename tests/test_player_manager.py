"""Tests for game/player_manager.py — PlayerManager unit tests (P0-4 validation)."""

from unittest.mock import MagicMock, PropertyMock

import pytest

from game.player import Identity
from game.player_manager import PlayerManager


def _mock_player(pid, name, alive=True, identity=Identity.REBEL):
    p = MagicMock()
    p.id = pid
    p.name = name
    p.is_alive = alive
    p.identity = identity
    equip = MagicMock()
    equip.distance_to_others = 0
    equip.distance_from_others = 0
    equip.attack_range = 1
    p.equipment = equip
    return p


class TestPlayerManagerQueries:
    def test_current_player(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        mgr.players = [p1, p2]
        mgr.current_player_index = 0
        assert mgr.current_player == p1

    def test_get_player_by_id_found(self):
        mgr = PlayerManager()
        p1 = _mock_player(10, "X")
        mgr.players = [p1]
        assert mgr.get_player_by_id(10) == p1

    def test_get_player_by_id_not_found(self):
        mgr = PlayerManager()
        mgr.players = [_mock_player(1, "A")]
        assert mgr.get_player_by_id(999) is None

    def test_get_alive_players(self):
        mgr = PlayerManager()
        alive = _mock_player(1, "A", alive=True)
        dead = _mock_player(2, "B", alive=False)
        mgr.players = [alive, dead]
        result = mgr.get_alive_players()
        assert result == [alive]

    def test_get_other_players(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        p2 = _mock_player(2, "B")
        p3 = _mock_player(3, "C", alive=False)
        mgr.players = [p1, p2, p3]
        result = mgr.get_other_players(p1)
        assert result == [p2]

    def test_get_all_other_players_includes_dead(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        p2 = _mock_player(2, "B")
        dead = _mock_player(3, "C", alive=False)
        mgr.players = [p1, p2, dead]
        result = mgr.get_all_other_players(p1)
        assert len(result) == 2
        assert p2 in result
        assert dead in result

    def test_get_next_player_wraps(self):
        mgr = PlayerManager()
        p1, p2, p3 = _mock_player(1, "A"), _mock_player(2, "B"), _mock_player(3, "C")
        mgr.players = [p1, p2, p3]
        assert mgr.get_next_player(p3) == p1

    def test_get_next_player_skips_dead(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        dead = _mock_player(2, "B", alive=False)
        p3 = _mock_player(3, "C")
        mgr.players = [p1, dead, p3]
        assert mgr.get_next_player(p1) == p3

    def test_get_next_player_default_current(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        mgr.players = [p1, p2]
        mgr.current_player_index = 0
        assert mgr.get_next_player() == p2

    def test_get_next_player_only_one_alive(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        dead = _mock_player(2, "B", alive=False)
        mgr.players = [p1, dead]
        assert mgr.get_next_player(p1) == p1

    def test_lord_player(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A", identity=Identity.LORD)
        p2 = _mock_player(2, "B", identity=Identity.REBEL)
        mgr.players = [p1, p2]
        assert mgr.lord_player == p1

    def test_lord_player_none(self):
        mgr = PlayerManager()
        mgr.players = [_mock_player(1, "A", identity=Identity.REBEL)]
        assert mgr.lord_player is None

    def test_lord_player_index(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A", identity=Identity.REBEL)
        p2 = _mock_player(2, "B", identity=Identity.LORD)
        mgr.players = [p1, p2]
        assert mgr.lord_player_index == 1

    def test_lord_player_index_default_zero(self):
        mgr = PlayerManager()
        mgr.players = [_mock_player(1, "A", identity=Identity.REBEL)]
        assert mgr.lord_player_index == 0


class TestPlayerManagerDistance:
    def test_distance_to_self_is_zero(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        mgr.players = [p1]
        assert mgr.calculate_distance(p1, p1) == 0

    def test_distance_two_players(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        mgr.players = [p1, p2]
        assert mgr.calculate_distance(p1, p2) == 1

    def test_distance_circular(self):
        mgr = PlayerManager()
        players = [_mock_player(i, f"P{i}") for i in range(4)]
        mgr.players = players
        # Distance from P0 to P2 should be 2 (min of clockwise=2, counter=2)
        assert mgr.calculate_distance(players[0], players[2]) == 2
        # P0 to P1 = 1
        assert mgr.calculate_distance(players[0], players[1]) == 1
        # P0 to P3 = 1 (counterclockwise)
        assert mgr.calculate_distance(players[0], players[3]) == 1

    def test_distance_with_horse_modifier(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        p1.equipment.distance_to_others = -1  # Attack horse
        mgr.players = [p1, p2]
        # base=1, modifier=-1, max(1, 0) = 1
        assert mgr.calculate_distance(p1, p2) == 1

    def test_distance_with_defense_horse(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        p2.equipment.distance_from_others = 1  # Defense horse
        mgr.players = [p1, p2]
        # base=1 + 1 = 2
        assert mgr.calculate_distance(p1, p2) == 2

    def test_distance_dead_player_returns_999(self):
        mgr = PlayerManager()
        alive1 = _mock_player(1, "A")
        alive2 = _mock_player(2, "B")
        dead = _mock_player(3, "C", alive=False)
        mgr.players = [alive1, alive2, dead]
        assert mgr.calculate_distance(alive1, dead) == 999

    def test_distance_single_alive_returns_zero(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        dead = _mock_player(2, "B", alive=False)
        mgr.players = [p1, dead]
        assert mgr.calculate_distance(p1, p1) == 0

    def test_is_in_attack_range_true(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        p1.equipment.attack_range = 2
        mgr.players = [p1, p2]
        assert mgr.is_in_attack_range(p1, p2) is True

    def test_is_in_attack_range_false(self):
        mgr = PlayerManager()
        players = [_mock_player(i, f"P{i}") for i in range(5)]
        players[0].equipment.attack_range = 1
        mgr.players = players
        assert mgr.is_in_attack_range(players[0], players[2]) is False

    def test_get_targets_in_range(self):
        mgr = PlayerManager()
        p1, p2, p3 = _mock_player(1, "A"), _mock_player(2, "B"), _mock_player(3, "C")
        p1.equipment.attack_range = 1
        mgr.players = [p1, p2, p3]
        targets = mgr.get_targets_in_range(p1)
        assert p2 in targets
        assert p3 in targets


class TestPlayerManagerTurnAdvance:
    def test_advance_turn_normal(self):
        mgr = PlayerManager()
        p1, p2, p3 = _mock_player(1, "A"), _mock_player(2, "B"), _mock_player(3, "C")
        mgr.players = [p1, p2, p3]
        mgr.current_player_index = 0
        mgr.advance_turn()
        assert mgr.current_player_index == 1

    def test_advance_turn_wraps(self):
        mgr = PlayerManager()
        p1, p2 = _mock_player(1, "A"), _mock_player(2, "B")
        mgr.players = [p1, p2]
        mgr.current_player_index = 1
        mgr.advance_turn()
        assert mgr.current_player_index == 0

    def test_advance_turn_skips_dead(self):
        mgr = PlayerManager()
        p1 = _mock_player(1, "A")
        dead = _mock_player(2, "B", alive=False)
        p3 = _mock_player(3, "C")
        mgr.players = [p1, dead, p3]
        mgr.current_player_index = 0
        mgr.advance_turn()
        assert mgr.current_player_index == 2
