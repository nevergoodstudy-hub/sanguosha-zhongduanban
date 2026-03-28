"""网络请求处理器测试."""

from unittest.mock import MagicMock

from game.actions import GameResponse, RequestType
from game.card import CardName, CardSuit
from game.request_handler import NetworkRequestHandler


def _make_engine():
    engine = MagicMock()
    engine.ui = None
    engine.ai_bots = {}
    return engine


def _make_player(player_id=1, is_ai=False, hand=None):
    player = MagicMock()
    player.id = player_id
    player.is_ai = is_ai
    player.hand = hand or []
    player.hand_count = len(player.hand)
    player.name = f"Player{player_id}"
    player.equipment.get_all_cards.return_value = []
    player.get_all_cards.return_value = list(player.hand)
    return player


def _make_card(card_id: str, name=CardName.SHA, suit=CardSuit.SPADE):
    card = MagicMock()
    card.id = card_id
    card.name = name
    card.suit = suit
    card.number = 1
    card.display_name = f"{name}{card_id}"
    card.to_dict.return_value = {
        "id": card_id,
        "name": name,
        "type": "basic",
        "subtype": "attack",
        "suit": suit.value,
        "number": 1,
    }
    return card


class TestNetworkRequestHandler:
    def test_request_shan_uses_network_callback_for_connected_human(self):
        engine = _make_engine()
        callback = MagicMock(
            return_value=GameResponse(
                request_type=RequestType.PLAY_SHAN,
                player_id=1,
                accepted=True,
                card_ids=["shan_heart_2"],
            )
        )
        handler = NetworkRequestHandler(engine, callback, connected_player_ids={1})
        player = _make_player(player_id=1, is_ai=False)
        shan = _make_card("shan_heart_2", name=CardName.SHAN, suit=CardSuit.HEART)
        player.get_cards_by_name.return_value = [shan]

        result = handler.request_shan(player)

        assert result is shan
        callback.assert_called_once()
        request = callback.call_args.args[0]
        assert request.request_type == RequestType.PLAY_SHAN
        assert request.player_id == 1
        assert request.options["cards"][0]["id"] == "shan_heart_2"

    def test_request_discard_returns_selected_cards(self):
        engine = _make_engine()
        callback = MagicMock(
            return_value=GameResponse(
                request_type=RequestType.DISCARD,
                player_id=1,
                accepted=True,
                card_ids=["sha_spade_A", "shan_heart_2"],
            )
        )
        handler = NetworkRequestHandler(engine, callback, connected_player_ids={1})
        card_a = _make_card("sha_spade_A", name=CardName.SHA)
        card_b = _make_card("shan_heart_2", name=CardName.SHAN, suit=CardSuit.HEART)
        player = _make_player(player_id=1, is_ai=False, hand=[card_a, card_b])

        result = handler.request_discard(player, 2, 2)

        assert result == [card_a, card_b]
        callback.assert_called_once()
        request = callback.call_args.args[0]
        assert request.request_type == RequestType.DISCARD
        assert request.min_cards == 2
        assert request.max_cards == 2

    def test_choose_card_from_player_hides_target_hand_cards(self):
        engine = _make_engine()
        hidden_card = _make_card("hidden_sha", name=CardName.SHA)
        equip_card = _make_card("public_weapon", name=CardName.ZHUGENU)
        chooser = _make_player(player_id=1, is_ai=False)
        target = _make_player(player_id=2, is_ai=False, hand=[hidden_card])
        target.get_all_cards.return_value = [hidden_card, equip_card]
        target.equipment.get_all_cards.return_value = [equip_card]

        def _callback(request):
            assert request.request_type == RequestType.CHOOSE_OPTION
            choices = request.options["choices"]
            hand_choice = next(choice for choice in choices if choice["zone"] == "hand")
            equip_choice = next(choice for choice in choices if choice["zone"] == "equipment")
            assert hand_choice["hidden"] is True
            assert "card" not in hand_choice
            assert equip_choice["card"]["id"] == "public_weapon"
            return GameResponse(
                request_type=RequestType.CHOOSE_OPTION,
                player_id=1,
                accepted=True,
                option=hand_choice["token"],
            )

        handler = NetworkRequestHandler(
            engine,
            MagicMock(side_effect=_callback),
            connected_player_ids={1},
        )

        result = handler.choose_card_from_player(chooser, target)

        assert result is hidden_card

    def test_guanxing_selection_uses_network_order(self):
        engine = _make_engine()
        cards = [
            _make_card("guanxing_1", name=CardName.SHA),
            _make_card("guanxing_2", name=CardName.SHAN),
            _make_card("guanxing_3", name=CardName.TAO),
        ]
        player = _make_player(player_id=1, is_ai=False)

        def _callback(request):
            assert request.request_type == RequestType.GUANXING
            assert [card["id"] for card in request.options["cards"]] == [
                "guanxing_1",
                "guanxing_2",
                "guanxing_3",
            ]
            return GameResponse(
                request_type=RequestType.GUANXING,
                player_id=1,
                accepted=True,
                card_ids=["guanxing_3", "guanxing_1"],
                option=["guanxing_2"],
            )

        handler = NetworkRequestHandler(
            engine,
            MagicMock(side_effect=_callback),
            connected_player_ids={1},
        )

        top_cards, bottom_cards = handler.guanxing_selection(player, cards)

        assert top_cards == [cards[2], cards[0]]
        assert bottom_cards == [cards[1]]

    def test_guanxing_selection_falls_back_on_invalid_network_order(self):
        engine = _make_engine()
        cards = [
            _make_card("guanxing_1", name=CardName.SHA),
            _make_card("guanxing_2", name=CardName.SHAN),
            _make_card("guanxing_3", name=CardName.TAO),
        ]
        player = _make_player(player_id=1, is_ai=False)
        callback = MagicMock(
            return_value=GameResponse(
                request_type=RequestType.GUANXING,
                player_id=1,
                accepted=True,
                card_ids=["guanxing_1", "guanxing_1"],
                option=["guanxing_3"],
            )
        )
        handler = NetworkRequestHandler(engine, callback, connected_player_ids={1})

        top_cards, bottom_cards = handler.guanxing_selection(player, cards)

        assert top_cards == [cards[0], cards[1]]
        assert bottom_cards == [cards[2]]

    def test_request_discard_falls_back_when_network_response_invalid(self):
        engine = _make_engine()
        callback = MagicMock(
            return_value=GameResponse(
                request_type=RequestType.DISCARD,
                player_id=1,
                accepted=True,
                card_ids=["sha_spade_A"],
            )
        )
        handler = NetworkRequestHandler(engine, callback, connected_player_ids={1})
        card_a = _make_card("sha_spade_A", name=CardName.SHA)
        card_b = _make_card("shan_heart_2", name=CardName.SHAN, suit=CardSuit.HEART)
        player = _make_player(player_id=1, is_ai=False, hand=[card_a, card_b])

        result = handler.request_discard(player, 2, 2)

        assert result == [card_a, card_b]
