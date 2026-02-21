"""Tests for game.request_handler.DefaultRequestHandler."""

from unittest.mock import MagicMock

from game.card import CardName, CardSuit
from game.request_handler import DefaultRequestHandler


def _make_engine():
    engine = MagicMock()
    engine.ui = MagicMock()
    return engine


def _make_player(is_ai=True, hand=None):
    player = MagicMock()
    player.is_ai = is_ai
    player.hand = hand or []
    player.name = "TestPlayer"
    return player


def _make_card(name=CardName.SHA, suit=CardSuit.SPADE):
    card = MagicMock()
    card.name = name
    card.suit = suit
    return card


# ==================== request_shan ====================


class TestRequestShan:
    def test_no_shan_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player()
        player.get_cards_by_name.return_value = []
        assert handler.request_shan(player) is None

    def test_ai_returns_first(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        shan = _make_card(CardName.SHAN)
        player.get_cards_by_name.return_value = [shan]
        assert handler.request_shan(player) is shan

    def test_human_with_ui(self):
        engine = _make_engine()
        shan = _make_card(CardName.SHAN)
        engine.ui.ask_for_shan.return_value = shan
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        player.get_cards_by_name.return_value = [shan]
        result = handler.request_shan(player)
        engine.ui.ask_for_shan.assert_called_once_with(player)

    def test_human_no_ui(self):
        engine = _make_engine()
        engine.ui = None
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        shan = _make_card(CardName.SHAN)
        player.get_cards_by_name.return_value = [shan]
        assert handler.request_shan(player) is shan


# ==================== request_sha ====================


class TestRequestSha:
    def test_no_sha_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player()
        player.get_cards_by_name.return_value = []
        assert handler.request_sha(player) is None

    def test_ai_returns_first(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        sha = _make_card(CardName.SHA)
        player.get_cards_by_name.return_value = [sha]
        assert handler.request_sha(player) is sha

    def test_human_with_ui(self):
        engine = _make_engine()
        sha = _make_card(CardName.SHA)
        engine.ui.ask_for_sha.return_value = sha
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        player.get_cards_by_name.return_value = [sha]
        handler.request_sha(player)
        engine.ui.ask_for_sha.assert_called_once_with(player)

    def test_human_no_ui(self):
        engine = _make_engine()
        engine.ui = None
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        sha = _make_card(CardName.SHA)
        player.get_cards_by_name.return_value = [sha]
        assert handler.request_sha(player) is sha


# ==================== request_tao ====================


class TestRequestTao:
    def test_no_tao_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        savior = _make_player()
        savior.get_cards_by_name.return_value = []
        dying = _make_player()
        assert handler.request_tao(savior, dying) is None

    def test_ai_should_save(self):
        engine = _make_engine()
        engine._ai_should_save.return_value = True
        handler = DefaultRequestHandler(engine)
        savior = _make_player(is_ai=True)
        tao = _make_card(CardName.TAO)
        savior.get_cards_by_name.return_value = [tao]
        dying = _make_player()
        assert handler.request_tao(savior, dying) is tao

    def test_ai_should_not_save(self):
        engine = _make_engine()
        engine._ai_should_save.return_value = False
        handler = DefaultRequestHandler(engine)
        savior = _make_player(is_ai=True)
        tao = _make_card(CardName.TAO)
        savior.get_cards_by_name.return_value = [tao]
        dying = _make_player()
        assert handler.request_tao(savior, dying) is None

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        savior = _make_player(is_ai=False)
        tao = _make_card(CardName.TAO)
        savior.get_cards_by_name.return_value = [tao]
        dying = _make_player()
        handler.request_tao(savior, dying)
        engine.ui.ask_for_tao.assert_called_once_with(savior, dying)

    def test_human_no_ui(self):
        engine = _make_engine()
        engine.ui = None
        handler = DefaultRequestHandler(engine)
        savior = _make_player(is_ai=False)
        tao = _make_card(CardName.TAO)
        savior.get_cards_by_name.return_value = [tao]
        dying = _make_player()
        assert handler.request_tao(savior, dying) is None


# ==================== request_wuxie ====================


class TestRequestWuxie:
    def test_no_wuxie_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player()
        player.get_cards_by_name.return_value = []
        assert handler.request_wuxie(player, MagicMock(), MagicMock(), None, False) is None

    def test_ai_should_wuxie(self):
        engine = _make_engine()
        engine._ai_should_wuxie.return_value = True
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        wuxie = _make_card(CardName.WUXIE)
        player.get_cards_by_name.return_value = [wuxie]
        result = handler.request_wuxie(player, MagicMock(), MagicMock(), None, False)
        assert result is wuxie

    def test_ai_should_not_wuxie(self):
        engine = _make_engine()
        engine._ai_should_wuxie.return_value = False
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        wuxie = _make_card(CardName.WUXIE)
        player.get_cards_by_name.return_value = [wuxie]
        assert handler.request_wuxie(player, MagicMock(), MagicMock(), None, False) is None

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        wuxie = _make_card(CardName.WUXIE)
        player.get_cards_by_name.return_value = [wuxie]
        trick = MagicMock()
        source = MagicMock()
        handler.request_wuxie(player, trick, source, None, True)
        engine.ui.ask_for_wuxie.assert_called_once_with(player, trick, source, None, True)

    def test_human_no_ui(self):
        engine = _make_engine()
        engine.ui = None
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        wuxie = _make_card(CardName.WUXIE)
        player.get_cards_by_name.return_value = [wuxie]
        assert handler.request_wuxie(player, MagicMock(), MagicMock(), None, False) is None


# ==================== choose_card_from_player ====================


class TestChooseCardFromPlayer:
    def test_no_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        chooser = _make_player()
        target = _make_player()
        target.get_all_cards.return_value = []
        assert handler.choose_card_from_player(chooser, target) is None

    def test_ai_random(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        chooser = _make_player(is_ai=True)
        target = _make_player()
        card = _make_card()
        target.get_all_cards.return_value = [card]
        result = handler.choose_card_from_player(chooser, target)
        assert result is card

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        chooser = _make_player(is_ai=False)
        target = _make_player()
        card = _make_card()
        target.get_all_cards.return_value = [card]
        handler.choose_card_from_player(chooser, target)
        engine.ui.choose_card_from_player.assert_called_once()

    def test_human_no_ui(self):
        engine = _make_engine()
        engine.ui = None
        handler = DefaultRequestHandler(engine)
        chooser = _make_player(is_ai=False)
        target = _make_player()
        card = _make_card()
        target.get_all_cards.return_value = [card]
        result = handler.choose_card_from_player(chooser, target)
        assert result is card


# ==================== choose_card_to_show ====================


class TestChooseCardToShow:
    def test_no_hand(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(hand=[])
        assert handler.choose_card_to_show(player) is None

    def test_ai(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        card = _make_card()
        player = _make_player(is_ai=True, hand=[card])
        result = handler.choose_card_to_show(player)
        assert result is card

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        card = _make_card()
        player = _make_player(is_ai=False, hand=[card])
        handler.choose_card_to_show(player)
        engine.ui.choose_card_to_show.assert_called_once()

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.choose_card_to_show
        handler = DefaultRequestHandler(engine)
        card = _make_card()
        player = _make_player(is_ai=False, hand=[card])
        result = handler.choose_card_to_show(player)
        assert result is card


# ==================== choose_card_to_discard_for_huogong ====================


class TestChooseCardToDiscardForHuogong:
    def test_no_matching(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True, hand=[_make_card(suit=CardSuit.HEART)])
        result = handler.choose_card_to_discard_for_huogong(player, CardSuit.SPADE)
        assert result is None

    def test_ai_matching(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        card = _make_card(suit=CardSuit.SPADE)
        player = _make_player(is_ai=True, hand=[card])
        result = handler.choose_card_to_discard_for_huogong(player, CardSuit.SPADE)
        assert result is card

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        card = _make_card(suit=CardSuit.SPADE)
        player = _make_player(is_ai=False, hand=[card])
        handler.choose_card_to_discard_for_huogong(player, CardSuit.SPADE)
        engine.ui.choose_card_to_discard_for_huogong.assert_called_once()

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.choose_card_to_discard_for_huogong
        handler = DefaultRequestHandler(engine)
        card = _make_card(suit=CardSuit.SPADE)
        player = _make_player(is_ai=False, hand=[card])
        result = handler.choose_card_to_discard_for_huogong(player, CardSuit.SPADE)
        assert result is card


# ==================== choose_suit ====================


class TestChooseSuit:
    def test_ai(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        result = handler.choose_suit(player)
        assert result in list(CardSuit)

    def test_human_with_ui(self):
        engine = _make_engine()
        engine.ui.choose_suit.return_value = CardSuit.HEART
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        result = handler.choose_suit(player)
        assert result == CardSuit.HEART

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.choose_suit
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        result = handler.choose_suit(player)
        assert result in list(CardSuit)


# ==================== guanxing_selection ====================


class TestGuanxingSelection:
    def test_ai_sorts_by_priority(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        cards = [
            _make_card(name=CardName.SHA),
            _make_card(name=CardName.TAO),
            _make_card(name=CardName.SHAN),
            _make_card(name=CardName.WUZHONG),
        ]
        top, bottom = handler.guanxing_selection(player, cards)
        assert len(top) + len(bottom) == 4

    def test_human_with_ui(self):
        engine = _make_engine()
        cards = [_make_card(), _make_card()]
        engine.ui.guanxing_selection.return_value = ([cards[0]], [cards[1]])
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        handler.guanxing_selection(player, cards)
        engine.ui.guanxing_selection.assert_called_once()

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.guanxing_selection
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        cards = [_make_card(), _make_card(), _make_card()]
        top, bottom = handler.guanxing_selection(player, cards)
        assert len(top) + len(bottom) == 3


# ==================== ask_zhuque_convert ====================


class TestAskZhuqueConvert:
    def test_ai_always_true(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        assert handler.ask_zhuque_convert(player) is True

    def test_human_with_ui(self):
        engine = _make_engine()
        engine.ui.ask_zhuque_convert.return_value = True
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        handler.ask_zhuque_convert(player)
        engine.ui.ask_zhuque_convert.assert_called_once()

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.ask_zhuque_convert
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        assert handler.ask_zhuque_convert(player) is False


# ==================== ask_for_jijiang ====================


class TestAskForJijiang:
    def test_no_sha_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player()
        player.get_cards_by_name.return_value = []
        assert handler.ask_for_jijiang(player) is None

    def test_ai(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        sha = _make_card(CardName.SHA)
        player.get_cards_by_name.return_value = [sha]
        assert handler.ask_for_jijiang(player) is sha

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        sha = _make_card(CardName.SHA)
        player.get_cards_by_name.return_value = [sha]
        handler.ask_for_jijiang(player)
        engine.ui.ask_for_jijiang.assert_called_once()

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.ask_for_jijiang
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        sha = _make_card(CardName.SHA)
        player.get_cards_by_name.return_value = [sha]
        assert handler.ask_for_jijiang(player) is None


# ==================== ask_for_hujia ====================


class TestAskForHujia:
    def test_no_shan_cards(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player()
        player.get_cards_by_name.return_value = []
        assert handler.ask_for_hujia(player) is None

    def test_ai(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=True)
        shan = _make_card(CardName.SHAN)
        player.get_cards_by_name.return_value = [shan]
        assert handler.ask_for_hujia(player) is shan

    def test_human_with_ui(self):
        engine = _make_engine()
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        shan = _make_card(CardName.SHAN)
        player.get_cards_by_name.return_value = [shan]
        handler.ask_for_hujia(player)
        engine.ui.ask_for_hujia.assert_called_once()

    def test_human_no_ui_attr(self):
        engine = _make_engine()
        del engine.ui.ask_for_hujia
        handler = DefaultRequestHandler(engine)
        player = _make_player(is_ai=False)
        shan = _make_card(CardName.SHAN)
        player.get_cards_by_name.return_value = [shan]
        assert handler.ask_for_hujia(player) is None
