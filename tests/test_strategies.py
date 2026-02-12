"""Tests for ai/strategy.py — shared AI utility functions."""

from unittest.mock import MagicMock

from game.card import Card, CardName, CardSubtype, CardSuit, CardType
from game.player import Identity

from ai.strategy import (
    card_priority,
    count_useless_cards,
    get_friends,
    is_enemy,
    pick_least_valuable,
    smart_discard,
)


def _mock_player(identity=Identity.LORD, alive=True, hand=None):
    p = MagicMock()
    p.identity = identity
    p.is_alive = alive
    p.hand = hand if hand is not None else []
    p.can_use_sha = MagicMock(return_value=True)
    p.get_cards_by_name = MagicMock(return_value=[])
    return p


def _make_card(name, card_type=CardType.BASIC, subtype=CardSubtype.ATTACK):
    return Card(
        id=f"test_{name}",
        name=name,
        card_type=card_type,
        subtype=subtype,
        suit=CardSuit.HEART,
        number=5,
    )


# ==================== is_enemy ====================


class TestIsEnemy:
    def test_lord_sees_rebel_as_enemy(self):
        lord = _mock_player(identity=Identity.LORD)
        rebel = _mock_player(identity=Identity.REBEL)
        assert is_enemy(lord, rebel) is True

    def test_lord_sees_spy_as_enemy(self):
        lord = _mock_player(identity=Identity.LORD)
        spy = _mock_player(identity=Identity.SPY)
        assert is_enemy(lord, spy) is True

    def test_lord_sees_loyalist_as_friend(self):
        lord = _mock_player(identity=Identity.LORD)
        loyalist = _mock_player(identity=Identity.LOYALIST)
        assert is_enemy(lord, loyalist) is False

    def test_rebel_sees_lord_as_enemy(self):
        rebel = _mock_player(identity=Identity.REBEL)
        lord = _mock_player(identity=Identity.LORD)
        assert is_enemy(rebel, lord) is True

    def test_rebel_sees_rebel_as_friend(self):
        r1 = _mock_player(identity=Identity.REBEL)
        r2 = _mock_player(identity=Identity.REBEL)
        assert is_enemy(r1, r2) is False

    def test_spy_sees_rebel_as_enemy_early(self):
        """Spy without engine: defaults to alive_count=3, sees rebels as enemy."""
        spy = _mock_player(identity=Identity.SPY)
        rebel = _mock_player(identity=Identity.REBEL)
        assert is_enemy(spy, rebel) is True

    def test_spy_sees_lord_as_friend_early(self):
        """Spy without engine: defaults to alive_count=3, protects lord."""
        spy = _mock_player(identity=Identity.SPY)
        lord = _mock_player(identity=Identity.LORD)
        assert is_enemy(spy, lord) is False

    def test_spy_last_duel_with_engine(self):
        """Spy with engine: 2 alive → all are enemies."""
        spy = _mock_player(identity=Identity.SPY)
        lord = _mock_player(identity=Identity.LORD)
        engine = MagicMock()
        engine.get_alive_players.return_value = [spy, lord]
        assert is_enemy(spy, lord, engine=engine) is True

    def test_spy_early_with_engine(self):
        """Spy with engine: 4 alive → rebels are enemies."""
        spy = _mock_player(identity=Identity.SPY)
        lord = _mock_player(identity=Identity.LORD)
        engine = MagicMock()
        engine.get_alive_players.return_value = [spy, lord, MagicMock(), MagicMock()]
        assert is_enemy(spy, lord, engine=engine) is False


# ==================== card_priority ====================


class TestCardPriority:
    def test_tao_highest(self):
        assert card_priority(_make_card(CardName.TAO, subtype=CardSubtype.HEAL)) == 100

    def test_wuxie_high(self):
        assert card_priority(_make_card(CardName.WUXIE, CardType.TRICK, CardSubtype.COUNTER)) == 90

    def test_shan_above_sha(self):
        shan = card_priority(_make_card(CardName.SHAN, subtype=CardSubtype.DODGE))
        sha = card_priority(_make_card(CardName.SHA))
        assert shan > sha

    def test_equipment_low(self):
        c = _make_card(CardName.QINGLONG, CardType.EQUIPMENT, CardSubtype.WEAPON)
        assert card_priority(c) == 30


# ==================== smart_discard ====================


class TestSmartDiscard:
    def test_empty_hand(self):
        p = _mock_player(hand=[])
        assert smart_discard(p, 2) == []

    def test_discards_low_priority_first(self):
        equip = _make_card(CardName.QINGLONG, CardType.EQUIPMENT, CardSubtype.WEAPON)
        tao = _make_card(CardName.TAO, subtype=CardSubtype.HEAL)
        p = _mock_player(hand=[tao, equip])
        p.can_use_sha = MagicMock(return_value=True)
        result = smart_discard(p, 1)
        assert result == [equip]


# ==================== get_friends ====================


class TestGetFriends:
    def test_lord_friends_include_loyalist(self):
        lord = _mock_player(identity=Identity.LORD)
        loyalist = _mock_player(identity=Identity.LOYALIST)
        rebel = _mock_player(identity=Identity.REBEL)
        engine = MagicMock()
        engine.get_other_players.return_value = [loyalist, rebel]
        friends = get_friends(lord, engine)
        assert loyalist in friends
        assert rebel not in friends


# ==================== pick_least_valuable ====================


class TestPickLeastValuable:
    def test_picks_equipment_over_tao(self):
        equip = _make_card(CardName.QINGLONG, CardType.EQUIPMENT, CardSubtype.WEAPON)
        tao = _make_card(CardName.TAO, subtype=CardSubtype.HEAL)
        p = _mock_player()
        result = pick_least_valuable([equip, tao], p)
        assert result == equip


# ==================== count_useless_cards ====================


class TestCountUselessCards:
    def test_no_useless(self):
        p = _mock_player(hand=[])
        engine = MagicMock()
        assert count_useless_cards(p, engine) == 0
