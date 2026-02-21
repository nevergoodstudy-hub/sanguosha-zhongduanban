"""Tests for game.phase_fsm module."""

import pytest

from game.enums import GamePhase
from game.phase_fsm import VALID_TRANSITIONS, InvalidPhaseTransition, PhaseFSM


class TestPhaseFSM:
    def test_initial_phase_is_prepare(self):
        fsm = PhaseFSM()
        assert fsm.current == GamePhase.PREPARE

    def test_valid_full_turn_cycle(self):
        fsm = PhaseFSM()
        fsm.transition(GamePhase.JUDGE)
        assert fsm.current == GamePhase.JUDGE
        fsm.transition(GamePhase.DRAW)
        assert fsm.current == GamePhase.DRAW
        fsm.transition(GamePhase.PLAY)
        assert fsm.current == GamePhase.PLAY
        fsm.transition(GamePhase.DISCARD)
        assert fsm.current == GamePhase.DISCARD
        fsm.transition(GamePhase.END)
        assert fsm.current == GamePhase.END

    def test_end_to_prepare_for_next_turn(self):
        fsm = PhaseFSM()
        fsm.transition(GamePhase.JUDGE)
        fsm.transition(GamePhase.DRAW)
        fsm.transition(GamePhase.PLAY)
        fsm.transition(GamePhase.DISCARD)
        fsm.transition(GamePhase.END)
        fsm.transition(GamePhase.PREPARE)
        assert fsm.current == GamePhase.PREPARE

    def test_invalid_skip_phase(self):
        fsm = PhaseFSM()
        with pytest.raises(InvalidPhaseTransition) as exc_info:
            fsm.transition(GamePhase.DRAW)  # skip JUDGE
        assert exc_info.value.from_phase == GamePhase.PREPARE
        assert exc_info.value.to_phase == GamePhase.DRAW

    def test_invalid_backward_transition(self):
        fsm = PhaseFSM()
        fsm.transition(GamePhase.JUDGE)
        fsm.transition(GamePhase.DRAW)
        with pytest.raises(InvalidPhaseTransition):
            fsm.transition(GamePhase.JUDGE)  # backward

    def test_invalid_same_phase_transition(self):
        fsm = PhaseFSM()
        with pytest.raises(InvalidPhaseTransition):
            fsm.transition(GamePhase.PREPARE)  # self-loop

    def test_can_transition(self):
        fsm = PhaseFSM()
        assert fsm.can_transition(GamePhase.JUDGE) is True
        assert fsm.can_transition(GamePhase.DRAW) is False
        assert fsm.can_transition(GamePhase.PLAY) is False

    def test_can_play_card(self):
        fsm = PhaseFSM()
        assert fsm.can_play_card() is False
        fsm.transition(GamePhase.JUDGE)
        assert fsm.can_play_card() is False
        fsm.transition(GamePhase.DRAW)
        assert fsm.can_play_card() is False
        fsm.transition(GamePhase.PLAY)
        assert fsm.can_play_card() is True
        fsm.transition(GamePhase.DISCARD)
        assert fsm.can_play_card() is False

    def test_reset(self):
        fsm = PhaseFSM()
        fsm.transition(GamePhase.JUDGE)
        fsm.transition(GamePhase.DRAW)
        fsm.reset()
        assert fsm.current == GamePhase.PREPARE

    def test_reset_allows_new_turn(self):
        fsm = PhaseFSM()
        fsm.transition(GamePhase.JUDGE)
        fsm.transition(GamePhase.DRAW)
        fsm.transition(GamePhase.PLAY)
        fsm.transition(GamePhase.DISCARD)
        fsm.transition(GamePhase.END)
        fsm.reset()
        # Should be able to start a new turn cycle
        fsm.transition(GamePhase.JUDGE)
        assert fsm.current == GamePhase.JUDGE


class TestValidTransitions:
    def test_all_phases_have_transitions(self):
        for phase in GamePhase:
            assert phase in VALID_TRANSITIONS

    def test_no_self_loops(self):
        for phase, targets in VALID_TRANSITIONS.items():
            assert phase not in targets

    def test_exactly_one_successor(self):
        """Each phase should have exactly one valid successor."""
        for phase, targets in VALID_TRANSITIONS.items():
            assert len(targets) == 1


class TestInvalidPhaseTransition:
    def test_exception_attributes(self):
        exc = InvalidPhaseTransition(GamePhase.DRAW, GamePhase.END)
        assert exc.from_phase == GamePhase.DRAW
        assert exc.to_phase == GamePhase.END
        assert "DRAW" in str(exc)
        assert "END" in str(exc)

    def test_inherits_from_game_error(self):
        from game.exceptions import GameError

        exc = InvalidPhaseTransition(GamePhase.DRAW, GamePhase.END)
        assert isinstance(exc, GameError)
