"""Tests for recursive Wuxie (无懈可击) nullification chain — P1-7 validation.

Validates:
- Depth 1: Single Wuxie cancels a trick card
- Depth 2: Counter-Wuxie restores the trick card
- Depth 3: Third Wuxie re-cancels the trick card
- Max depth limit prevents infinite chain
"""

from unittest.mock import MagicMock, PropertyMock, call

import pytest

from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.combat import CombatSystem


def _make_card(name=CardName.WUXIE, suit=CardSuit.SPADE, number=1):
    subtype = CardSubtype.COUNTER if name == CardName.WUXIE else CardSubtype.SINGLE_TARGET
    return Card(
        id=f"test_{name}_{suit.value}_{number}",
        name=name,
        card_type=CardType.TRICK,
        subtype=subtype,
        suit=suit,
        number=number,
    )


def _make_player(name, alive=True, wuxie_count=0):
    p = MagicMock()
    p.name = name
    p.is_alive = alive
    p.id = id(p)

    wuxie_cards = [_make_card(number=i + 1) for i in range(wuxie_count)]
    # get_cards_by_name returns wuxie cards, shrinking as they're consumed
    _remaining = list(wuxie_cards)

    def get_cards(card_name):
        if card_name == CardName.WUXIE:
            return list(_remaining)
        return []

    def remove_card(card):
        if card in _remaining:
            _remaining.remove(card)

    p.get_cards_by_name = MagicMock(side_effect=get_cards)
    p.remove_card = MagicMock(side_effect=remove_card)
    return p


def _mock_ctx(players):
    ctx = MagicMock()
    ctx.players = players
    ctx.deck = MagicMock()
    ctx.deck.discard = MagicMock()
    ctx.log_event = MagicMock()
    ctx.request_handler = MagicMock()
    return ctx


class TestWuxieChainDepth:
    """Test recursive Wuxie nullification chain at various depths."""

    def test_no_wuxie_not_cancelled(self):
        """No one has Wuxie → trick not cancelled."""
        p1 = _make_player("Source")
        p2 = _make_player("Target")
        ctx = _mock_ctx([p1, p2])
        ctx.request_handler.request_wuxie.return_value = None
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.GUOHE)
        result = combat.request_wuxie(trick, p1, p2)
        assert result is False

    def test_depth_1_single_wuxie_cancels(self):
        """Depth 1: One player uses Wuxie → trick is cancelled."""
        source = _make_player("Source")
        target = _make_player("Target")
        responder = _make_player("Responder", wuxie_count=1)
        ctx = _mock_ctx([source, target, responder])

        wuxie_card = _make_card()
        call_count = [0]

        def request_wuxie_side_effect(resp, trick, src, tgt, is_cancelled):
            call_count[0] += 1
            if resp == responder and call_count[0] == 1:
                return wuxie_card
            return None

        ctx.request_handler.request_wuxie.side_effect = request_wuxie_side_effect
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.NANMAN)
        result = combat.request_wuxie(trick, source, target)
        assert result is True  # Cancelled at depth 1

    def test_depth_2_counter_wuxie_restores(self):
        """Depth 2: Wuxie then counter-Wuxie → trick NOT cancelled (restored)."""
        source = _make_player("Source")
        target = _make_player("Target")
        r1 = _make_player("R1", wuxie_count=1)
        r2 = _make_player("R2", wuxie_count=1)
        ctx = _mock_ctx([source, target, r1, r2])

        wuxie1 = _make_card(number=1)
        wuxie2 = _make_card(number=2)
        call_count = [0]

        def request_wuxie_side_effect(resp, trick, src, tgt, is_cancelled):
            call_count[0] += 1
            # Round 1: R1 cancels (depth 0→1, is_cancelled becomes True)
            if resp == r1 and not is_cancelled:
                return wuxie1
            # Round 2: R2 counter-cancels (depth 1→2, is_cancelled becomes False)
            if resp == r2 and is_cancelled:
                return wuxie2
            return None

        ctx.request_handler.request_wuxie.side_effect = request_wuxie_side_effect
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.WANJIAN)
        result = combat.request_wuxie(trick, source, target)
        assert result is False  # Restored at depth 2

    def test_depth_3_re_cancels(self):
        """Depth 3: Wuxie → counter-Wuxie → re-Wuxie → trick IS cancelled."""
        source = _make_player("Source")
        target = _make_player("Target")
        r1 = _make_player("R1", wuxie_count=2)
        r2 = _make_player("R2", wuxie_count=1)
        ctx = _mock_ctx([source, target, r1, r2])

        wuxie_a = _make_card(number=10)
        wuxie_b = _make_card(number=11)
        wuxie_c = _make_card(number=12)
        depth_tracker = [0]

        def request_wuxie_side_effect(resp, trick, src, tgt, is_cancelled):
            d = depth_tracker[0]
            # Depth 0→1: R1 cancels
            if d == 0 and resp == r1 and not is_cancelled:
                depth_tracker[0] += 1
                return wuxie_a
            # Depth 1→2: R2 counter-cancels
            if d == 1 and resp == r2 and is_cancelled:
                depth_tracker[0] += 1
                return wuxie_b
            # Depth 2→3: R1 re-cancels
            if d == 2 and resp == r1 and not is_cancelled:
                depth_tracker[0] += 1
                return wuxie_c
            return None

        ctx.request_handler.request_wuxie.side_effect = request_wuxie_side_effect
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.GUOHE)
        result = combat.request_wuxie(trick, source, target)
        assert result is True  # Re-cancelled at depth 3

    def test_wuxie_on_wuxie_card_returns_false(self):
        """Cannot Wuxie a Wuxie card itself (early return)."""
        source = _make_player("Source")
        ctx = _mock_ctx([source])
        combat = CombatSystem(ctx)

        wuxie = _make_card(CardName.WUXIE)
        result = combat.request_wuxie(wuxie, source)
        assert result is False

    def test_max_depth_terminates(self):
        """Chain terminates at _WUXIE_MAX_DEPTH to prevent infinite loop."""
        players = [_make_player(f"P{i}", wuxie_count=20) for i in range(4)]
        ctx = _mock_ctx(players)

        infinite_wuxie = _make_card()

        def always_wuxie(resp, trick, src, tgt, is_cancelled):
            return infinite_wuxie

        ctx.request_handler.request_wuxie.side_effect = always_wuxie
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.NANMAN)
        # Should not hang — terminates at max depth
        result = combat.request_wuxie(trick, players[0], players[1])
        # Result depends on whether max_depth is even/odd (10 is even → cancelled)
        assert isinstance(result, bool)

    def test_dead_players_skipped(self):
        """Dead players are skipped in the Wuxie response chain."""
        source = _make_player("Source")
        dead = _make_player("Dead", alive=False, wuxie_count=5)
        alive = _make_player("Alive", wuxie_count=0)
        ctx = _mock_ctx([source, dead, alive])
        ctx.request_handler.request_wuxie.return_value = None
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.GUOHE)
        result = combat.request_wuxie(trick, source, alive)
        assert result is False
        # Dead player should never be asked
        for c in ctx.request_handler.request_wuxie.call_args_list:
            assert c[0][0] != dead

    def test_player_without_wuxie_not_asked(self):
        """Players without Wuxie cards are not asked to respond."""
        source = _make_player("Source")
        no_wuxie = _make_player("NoWuxie", wuxie_count=0)
        ctx = _mock_ctx([source, no_wuxie])
        combat = CombatSystem(ctx)

        trick = _make_card(CardName.NANMAN)
        result = combat.request_wuxie(trick, source, no_wuxie)
        assert result is False
        ctx.request_handler.request_wuxie.assert_not_called()
