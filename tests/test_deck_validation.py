"""Deck integrity validation tests (P2-6)."""

import pytest

from game.card import Card, CardSubtype, CardSuit, CardType, Deck


class TestDeckValidation:
    """Test Deck.validate_deck() method."""

    def test_validate_deck_passes_on_standard_deck(self):
        """Standard cards.json deck should validate without errors."""
        deck = Deck("data/cards.json")
        errors = deck.validate_deck()
        assert errors == [], f"Validation errors: {errors}"

    def test_validate_deck_detects_missing_card(self):
        """Removing a card should trigger a validation error."""
        deck = Deck("data/cards.json")
        # Remove one 杀 from _all_cards
        for i, card in enumerate(deck._all_cards):
            if card.name == "杀":
                deck._all_cards.pop(i)
                break
        errors = deck.validate_deck()
        assert any("杀" in e and "expected 21" in e for e in errors)

    def test_validate_deck_detects_extra_card(self):
        """Adding an unexpected card should trigger validation error."""
        deck = Deck("data/cards.json")
        fake_card = Card(
            id="fake_card",
            name="假牌",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=1,
        )
        deck._all_cards.append(fake_card)
        errors = deck.validate_deck()
        assert any("unexpected card" in e and "假牌" in e for e in errors)

    def test_validate_deck_empty_deck(self):
        """Empty deck should report all expected cards as missing."""
        deck = Deck()
        errors = deck.validate_deck()
        assert len(errors) == len(Deck.EXPECTED_CARD_COUNTS)

    def test_validate_deck_count_mismatch(self):
        """Duplicating a card should trigger count mismatch."""
        deck = Deck("data/cards.json")
        # Add a duplicate 闪
        for card in deck._all_cards:
            if card.name == "闪":
                deck._all_cards.append(card)
                break
        errors = deck.validate_deck()
        assert any("闪" in e and "expected 14" in e and "got 15" in e for e in errors)

    def test_expected_card_counts_complete(self):
        """EXPECTED_CARD_COUNTS should cover all cards in cards.json."""
        deck = Deck("data/cards.json")
        names_in_deck = {c.name for c in deck._all_cards}
        names_in_expected = set(Deck.EXPECTED_CARD_COUNTS.keys())
        assert names_in_deck == names_in_expected
