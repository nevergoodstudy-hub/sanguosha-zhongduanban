"""Tests for game.game_controller pure-logic helper methods."""

from unittest.mock import MagicMock, patch

import pytest

from game.card import CardName, CardType
from game.engine import GamePhase, GameState
from game.game_controller import GameController
from game.player import Identity


def _make_ui():
    ui = MagicMock()
    return ui


def _make_controller(ui=None, engine=None):
    """Create a controller with mocked UI and engine."""
    with patch("game.game_controller.AIDifficulty", create=True):
        ui = ui or _make_ui()
        ctrl = GameController(ui)
        if engine:
            ctrl.engine = engine
        return ctrl


def _make_engine():
    engine = MagicMock()
    engine.phase = GamePhase.PLAY
    engine.players = []
    engine.ai_bots = {}
    engine.round_count = 1
    engine.is_game_over.return_value = False
    engine.skill_system = MagicMock()
    engine.state = GameState.IN_PROGRESS
    return engine


def _make_card(name=CardName.SHA, card_type=CardType.BASIC):
    card = MagicMock()
    card.name = name
    card.card_type = card_type
    card.display_name = str(name)
    return card


def _make_player(is_ai=False, hp=4, max_hp=4, hand=None):
    player = MagicMock()
    player.is_ai = is_ai
    player.hp = hp
    player.max_hp = max_hp
    player.hand = hand or []
    player.hand_count = len(player.hand)
    player.hero = MagicMock()
    player.hero.name = "TestHero"
    player.name = "Player1"
    player.need_discard = 0
    player.identity = Identity.LORD
    return player


# ==================== __init__ ====================


class TestInit:
    def test_constructor(self):
        ctrl = _make_controller()
        assert ctrl.engine is None
        assert ctrl.is_running is True

    def test_constructor_with_difficulty(self):
        from ai.bot import AIDifficulty

        ui = _make_ui()
        ctrl = GameController(ui, AIDifficulty.HARD)
        assert ctrl.ai_difficulty == AIDifficulty.HARD


# ==================== _check_card_usable ====================


class TestCheckCardUsable:
    def test_equipment_always_usable(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(card_type=CardType.EQUIPMENT)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is True

    def test_sha_cannot_use(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(name=CardName.SHA)
        player = _make_player()
        player.can_use_sha.return_value = False
        assert ctrl._check_card_usable(player, card) is False

    def test_sha_no_targets_in_range(self):
        engine = _make_engine()
        engine.get_targets_in_range.return_value = []
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.SHA)
        player = _make_player()
        player.can_use_sha.return_value = True
        assert ctrl._check_card_usable(player, card) is False

    def test_sha_ok(self):
        engine = _make_engine()
        engine.get_targets_in_range.return_value = [MagicMock()]
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.SHA)
        player = _make_player()
        player.can_use_sha.return_value = True
        assert ctrl._check_card_usable(player, card) is True

    def test_tao_hp_full(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(name=CardName.TAO)
        player = _make_player(hp=4, max_hp=4)
        assert ctrl._check_card_usable(player, card) is False

    def test_tao_hp_low(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(name=CardName.TAO)
        player = _make_player(hp=2, max_hp=4)
        assert ctrl._check_card_usable(player, card) is True

    def test_shan_not_usable(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(name=CardName.SHAN)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is False

    def test_juedou_with_others(self):
        engine = _make_engine()
        engine.get_other_players.return_value = [MagicMock()]
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.JUEDOU)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is True

    def test_juedou_no_others(self):
        engine = _make_engine()
        engine.get_other_players.return_value = []
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.JUEDOU)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is False

    def test_guohe_with_valid_targets(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = True
        engine.get_other_players.return_value = [target]
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.GUOHE)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is True

    def test_guohe_no_valid_targets(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = False
        engine.get_other_players.return_value = [target]
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.GUOHE)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is False

    def test_shunshou_in_range(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = True
        engine.get_other_players.return_value = [target]
        engine.calculate_distance.return_value = 1
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.SHUNSHOU)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is True

    def test_shunshou_out_of_range(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = True
        engine.get_other_players.return_value = [target]
        engine.calculate_distance.return_value = 3
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.SHUNSHOU)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is False

    def test_other_cards_usable(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(name=CardName.WUZHONG)
        player = _make_player()
        assert ctrl._check_card_usable(player, card) is True


# ==================== _has_usable_cards / _can_do_anything ====================


class TestHasUsableCards:
    def test_empty_hand(self):
        ctrl = _make_controller(engine=_make_engine())
        player = _make_player(hand=[])
        assert ctrl._has_usable_cards(player) is False

    def test_has_usable(self):
        engine = _make_engine()
        engine.get_targets_in_range.return_value = [MagicMock()]
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.SHA)
        player = _make_player(hand=[card])
        player.can_use_sha.return_value = True
        assert ctrl._has_usable_cards(player) is True

    def test_no_usable(self):
        ctrl = _make_controller(engine=_make_engine())
        card = _make_card(name=CardName.SHAN)
        player = _make_player(hand=[card])
        assert ctrl._has_usable_cards(player) is False


class TestHasUsableSkills:
    def test_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        player = _make_player()
        assert ctrl._has_usable_skills(player) is False

    def test_no_skill_system(self):
        engine = _make_engine()
        engine.skill_system = None
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        assert ctrl._has_usable_skills(player) is False

    def test_has_skills(self):
        engine = _make_engine()
        engine.skill_system.get_usable_skills.return_value = ["wusheng"]
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        assert ctrl._has_usable_skills(player) is True

    def test_no_skills(self):
        engine = _make_engine()
        engine.skill_system.get_usable_skills.return_value = []
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        assert ctrl._has_usable_skills(player) is False


class TestCanDoAnything:
    def test_can_play_card(self):
        engine = _make_engine()
        engine.get_targets_in_range.return_value = [MagicMock()]
        engine.skill_system.get_usable_skills.return_value = []
        ctrl = _make_controller(engine=engine)
        card = _make_card(name=CardName.SHA)
        player = _make_player(hand=[card])
        player.can_use_sha.return_value = True
        assert ctrl._can_do_anything(player) is True

    def test_cannot_do_anything(self):
        engine = _make_engine()
        engine.skill_system.get_usable_skills.return_value = []
        ctrl = _make_controller(engine=engine)
        player = _make_player(hand=[])
        assert ctrl._can_do_anything(player) is False


# ==================== get_playable_mask ====================


class TestGetPlayableMask:
    def test_returns_correct_mask(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        sha_card = _make_card(name=CardName.SHA)
        shan_card = _make_card(name=CardName.SHAN)
        equip_card = _make_card(card_type=CardType.EQUIPMENT)
        player = _make_player(hand=[sha_card, shan_card, equip_card])
        player.can_use_sha.return_value = False

        mask = ctrl.get_playable_mask(player)
        assert len(mask) == 3
        assert mask[0] is False  # sha can't use
        assert mask[1] is False  # shan passive
        assert mask[2] is True  # equipment always usable


class TestUpdatePlayableMask:
    def test_play_phase(self):
        engine = _make_engine()
        engine.phase = GamePhase.PLAY
        ctrl = _make_controller(engine=engine)
        player = _make_player(hand=[])
        ctrl._update_playable_mask(player)
        assert engine._playable_mask == []

    def test_not_play_phase(self):
        engine = _make_engine()
        engine.phase = GamePhase.DRAW
        ctrl = _make_controller(engine=engine)
        player = _make_player(hand=[_make_card()])
        ctrl._update_playable_mask(player)
        assert engine._playable_mask == []


# ==================== _show_turn_header ====================


class TestShowTurnHeader:
    def test_shows_header(self):
        engine = _make_engine()
        engine.round_count = 3
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        ctrl._show_turn_header(player)
        assert ctrl.ui.show_log.call_count >= 3  # multiple lines


# ==================== Phase execution helpers ====================


class TestPhaseExecution:
    def test_execute_prepare_phase(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        ctrl._execute_prepare_phase(player)
        engine.phase_prepare.assert_called_once_with(player)

    def test_execute_draw_phase(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(is_ai=True)
        player.hand_count = 4
        ctrl._execute_draw_phase(player)
        engine.phase_draw.assert_called_once_with(player)

    def test_execute_draw_phase_human(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(is_ai=False)
        player.hand_count = 4
        ctrl._execute_draw_phase(player)
        engine.phase_draw.assert_called_once()

    def test_execute_end_phase_ai(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(is_ai=True)
        ctrl._execute_end_phase(player)
        engine.phase_end.assert_called_once_with(player)

    def test_execute_end_phase_human(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(is_ai=False)
        ctrl._execute_end_phase(player)
        engine.phase_end.assert_called_once()

    def test_execute_discard_phase_no_discard(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        player.need_discard = 0
        ctrl._execute_discard_phase(player)
        # Should do nothing
        engine.phase_discard.assert_not_called()

    def test_execute_discard_phase_ai(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(is_ai=True)
        player.need_discard = 2
        ctrl._execute_discard_phase(player)
        engine.phase_discard.assert_called_once_with(player)


# ==================== _handle_game_over ====================


class TestHandleGameOver:
    def test_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        ctrl._handle_game_over()  # no error

    def test_lord_wins_lord_player(self):
        engine = _make_engine()
        engine.get_winner_message.return_value = "Lord wins!"
        engine.winner_identity = Identity.LORD
        human = MagicMock()
        human.identity = Identity.LORD
        engine.human_player = human
        ctrl = _make_controller(engine=engine)

        ctrl._handle_game_over()
        ctrl.ui.show_game_over.assert_called_once_with("Lord wins!", True)

    def test_lord_wins_loyalist_player(self):
        engine = _make_engine()
        engine.get_winner_message.return_value = "Lord wins!"
        engine.winner_identity = Identity.LORD
        human = MagicMock()
        human.identity = Identity.LOYALIST
        engine.human_player = human
        ctrl = _make_controller(engine=engine)

        ctrl._handle_game_over()
        ctrl.ui.show_game_over.assert_called_once_with("Lord wins!", True)

    def test_rebel_wins_rebel_player(self):
        engine = _make_engine()
        engine.get_winner_message.return_value = "Rebels win!"
        engine.winner_identity = Identity.REBEL
        human = MagicMock()
        human.identity = Identity.REBEL
        engine.human_player = human
        ctrl = _make_controller(engine=engine)

        ctrl._handle_game_over()
        ctrl.ui.show_game_over.assert_called_once_with("Rebels win!", True)

    def test_spy_wins_spy_player(self):
        engine = _make_engine()
        engine.get_winner_message.return_value = "Spy wins!"
        engine.winner_identity = Identity.SPY
        human = MagicMock()
        human.identity = Identity.SPY
        engine.human_player = human
        ctrl = _make_controller(engine=engine)

        ctrl._handle_game_over()
        ctrl.ui.show_game_over.assert_called_once_with("Spy wins!", True)

    def test_loss(self):
        engine = _make_engine()
        engine.get_winner_message.return_value = "Lord wins!"
        engine.winner_identity = Identity.LORD
        human = MagicMock()
        human.identity = Identity.REBEL
        engine.human_player = human
        ctrl = _make_controller(engine=engine)

        ctrl._handle_game_over()
        ctrl.ui.show_game_over.assert_called_once_with("Lord wins!", False)

    def test_no_human_player(self):
        engine = _make_engine()
        engine.get_winner_message.return_value = "Game over"
        engine.human_player = None
        ctrl = _make_controller(engine=engine)

        ctrl._handle_game_over()
        ctrl.ui.show_game_over.assert_called_once_with("Game over", False)


# ==================== Edge cases for _run_ai_turn / _run_human_turn ====================


class TestRunTurnEdgeCases:
    @pytest.mark.asyncio
    async def test_run_ai_turn_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        await ctrl._run_ai_turn(MagicMock())  # should not raise

    @pytest.mark.asyncio
    async def test_run_human_turn_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        await ctrl._run_human_turn(MagicMock())  # should not raise

    @pytest.mark.asyncio
    async def test_game_loop_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        await ctrl._game_loop()  # should not raise

    def test_choose_heroes_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        ctrl._choose_heroes()  # should not raise

    def test_setup_ai_bots_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        ctrl._setup_ai_bots()  # should not raise

    @pytest.mark.asyncio
    async def test_human_play_phase_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        await ctrl._human_play_phase(MagicMock())  # should not raise

    def test_handle_play_specific_card_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        ctrl._handle_play_specific_card(MagicMock(), MagicMock())  # should not raise

    @pytest.mark.asyncio
    async def test_handle_use_skill_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        await ctrl._handle_use_skill(MagicMock())  # should not raise

    def test_human_discard_phase_no_engine(self):
        ctrl = _make_controller()
        ctrl.engine = None
        ctrl._human_discard_phase(MagicMock())  # should not raise


# ==================== _handle_play_specific_card branches ====================


class TestHandlePlaySpecificCard:
    def test_equipment(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(card_type=CardType.EQUIPMENT)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_sha_with_target(self):
        engine = _make_engine()
        target = MagicMock(name="Target")
        engine.get_targets_in_range.return_value = [target]
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        player.can_use_sha.return_value = True
        ctrl.ui.choose_target.return_value = target
        card = _make_card(name=CardName.SHA)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_sha_no_targets(self):
        engine = _make_engine()
        engine.get_targets_in_range.return_value = []
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        player.can_use_sha.return_value = True
        card = _make_card(name=CardName.SHA)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_sha_cannot_use_no_paoxiao(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        player.can_use_sha.return_value = False
        player.has_skill.return_value = False
        card = _make_card(name=CardName.SHA)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_sha_cannot_use_has_paoxiao(self):
        engine = _make_engine()
        target = MagicMock()
        engine.get_targets_in_range.return_value = [target]
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        player.can_use_sha.return_value = False
        player.has_skill.return_value = True
        ctrl.ui.choose_target.return_value = target
        card = _make_card(name=CardName.SHA)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_tao_hp_full(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(hp=4, max_hp=4)
        card = _make_card(name=CardName.TAO, card_type=CardType.BASIC)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_tao_ok(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player(hp=2, max_hp=4)
        card = _make_card(name=CardName.TAO, card_type=CardType.BASIC)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_shan_not_playable(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.SHAN, card_type=CardType.BASIC)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_wuzhong(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.WUZHONG, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_nanman(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.NANMAN, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_taoyuan(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.TAOYUAN, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_juedou_with_target(self):
        engine = _make_engine()
        target = MagicMock()
        engine.get_other_players.return_value = [target]
        ctrl = _make_controller(engine=engine)
        ctrl.ui.choose_target.return_value = target
        player = _make_player()
        card = _make_card(name=CardName.JUEDOU, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_juedou_no_others(self):
        engine = _make_engine()
        engine.get_other_players.return_value = []
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.JUEDOU, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_guohe_with_target(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = True
        engine.get_other_players.return_value = [target]
        ctrl = _make_controller(engine=engine)
        ctrl.ui.choose_target.return_value = target
        player = _make_player()
        card = _make_card(name=CardName.GUOHE, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_guohe_no_valid_targets(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = False
        engine.get_other_players.return_value = [target]
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.GUOHE, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_shunshou_with_target(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = True
        engine.get_other_players.return_value = [target]
        engine.calculate_distance.return_value = 1
        ctrl = _make_controller(engine=engine)
        ctrl.ui.choose_target.return_value = target
        player = _make_player()
        card = _make_card(name=CardName.SHUNSHOU, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()

    def test_shunshou_no_valid(self):
        engine = _make_engine()
        target = MagicMock()
        target.has_any_card.return_value = True
        engine.get_other_players.return_value = [target]
        engine.calculate_distance.return_value = 5
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.SHUNSHOU, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_not_called()

    def test_other_card(self):
        engine = _make_engine()
        ctrl = _make_controller(engine=engine)
        player = _make_player()
        card = _make_card(name=CardName.TIESUO, card_type=CardType.TRICK)
        ctrl._handle_play_specific_card(player, card)
        engine.use_card.assert_called_once()
