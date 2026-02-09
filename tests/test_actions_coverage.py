"""Tests for game.actions module — action classes and enums."""

from unittest.mock import MagicMock

from game.actions import (
    ActionType,
    DiscardAction,
    PlayCardAction,
    RequestType,
    UseSkillAction,
)


class TestActionType:
    def test_all_types(self):
        names = {e.name for e in ActionType}
        assert "PLAY_CARD" in names
        assert "USE_SKILL" in names
        assert "DISCARD" in names
        assert "EQUIP" in names
        assert "RESPOND" in names
        assert "END_PHASE" in names


class TestRequestType:
    def test_all_types(self):
        names = {e.name for e in RequestType}
        assert "PLAY_SHAN" in names
        assert "PLAY_SHA" in names
        assert "PLAY_TAO" in names
        assert "PLAY_WUXIE" in names
        assert "CHOOSE_TARGET" in names
        assert "CHOOSE_SUIT" in names
        assert "GUANXING" in names
        assert "DISCARD" in names


class TestPlayCardAction:
    def _make_engine(self, player=None, current_player_id=0):
        engine = MagicMock()
        if player:
            engine.get_player_by_id.return_value = player
            engine.current_player = MagicMock()
            engine.current_player.id = current_player_id
        else:
            engine.get_player_by_id.return_value = None
        return engine

    def test_validate_no_player(self):
        engine = self._make_engine(player=None)
        action = PlayCardAction(player_id=1, card_id=99)
        ok, msg = action.validate(engine)
        assert ok is False
        assert "不存在" in msg

    def test_validate_not_your_turn(self):
        player = MagicMock()
        player.hand = []
        engine = self._make_engine(player=player, current_player_id=2)
        action = PlayCardAction(player_id=1, card_id=99)
        ok, msg = action.validate(engine)
        assert ok is False
        assert "回合" in msg

    def test_validate_card_not_found(self):
        player = MagicMock()
        player.hand = []
        engine = self._make_engine(player=player, current_player_id=1)
        action = PlayCardAction(player_id=1, card_id=99)
        ok, msg = action.validate(engine)
        assert ok is False
        assert "卡牌" in msg

    def test_validate_ok(self):
        card = MagicMock()
        card.id = 42
        player = MagicMock()
        player.hand = [card]
        engine = self._make_engine(player=player, current_player_id=1)
        action = PlayCardAction(player_id=1, card_id=42)
        ok, msg = action.validate(engine)
        assert ok is True

    def test_execute_invalid(self):
        engine = self._make_engine(player=None)
        action = PlayCardAction(player_id=1, card_id=99)
        assert action.execute(engine) is False

    def test_execute_ok(self):
        card = MagicMock()
        card.id = 42
        player = MagicMock()
        player.hand = [card]
        engine = self._make_engine(player=player, current_player_id=1)
        engine.use_card.return_value = True
        action = PlayCardAction(player_id=1, card_id=42)
        assert action.execute(engine) is True
        engine.use_card.assert_called_once()

    def test_action_type(self):
        action = PlayCardAction(player_id=1)
        assert action.action_type == ActionType.PLAY_CARD

    def test_timestamp_set(self):
        action = PlayCardAction(player_id=1)
        assert action.timestamp > 0


class TestUseSkillAction:
    def test_validate_no_player(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = None
        action = UseSkillAction(player_id=1, skill_id="wusheng")
        ok, msg = action.validate(engine)
        assert ok is False

    def test_validate_no_skill_system(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = MagicMock()
        engine.skill_system = None
        action = UseSkillAction(player_id=1, skill_id="wusheng")
        ok, msg = action.validate(engine)
        assert ok is False
        assert "技能系统" in msg

    def test_validate_cannot_use(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = MagicMock()
        engine.skill_system.can_use_skill.return_value = False
        action = UseSkillAction(player_id=1, skill_id="wusheng")
        ok, msg = action.validate(engine)
        assert ok is False

    def test_validate_ok(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = MagicMock()
        engine.skill_system.can_use_skill.return_value = True
        action = UseSkillAction(player_id=1, skill_id="wusheng")
        ok, msg = action.validate(engine)
        assert ok is True

    def test_execute_invalid(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = None
        action = UseSkillAction(player_id=1, skill_id="wusheng")
        assert action.execute(engine) is False

    def test_execute_ok(self):
        card = MagicMock()
        card.id = 10
        player = MagicMock()
        player.hand = [card]
        engine = MagicMock()
        engine.get_player_by_id.return_value = player
        engine.skill_system.can_use_skill.return_value = True
        engine.skill_system.use_skill.return_value = True
        action = UseSkillAction(player_id=1, skill_id="wusheng", card_ids=[10])
        assert action.execute(engine) is True

    def test_action_type(self):
        action = UseSkillAction(player_id=1)
        assert action.action_type == ActionType.USE_SKILL


class TestDiscardAction:
    def test_validate_no_player(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = None
        action = DiscardAction(player_id=1, card_ids=[1])
        ok, msg = action.validate(engine)
        assert ok is False

    def test_validate_no_cards(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = MagicMock()
        action = DiscardAction(player_id=1, card_ids=[])
        ok, msg = action.validate(engine)
        assert ok is False
        assert "未选择" in msg

    def test_validate_ok(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = MagicMock()
        action = DiscardAction(player_id=1, card_ids=[1, 2])
        ok, msg = action.validate(engine)
        assert ok is True

    def test_execute_invalid(self):
        engine = MagicMock()
        engine.get_player_by_id.return_value = None
        action = DiscardAction(player_id=1, card_ids=[1])
        assert action.execute(engine) is False

    def test_execute_ok(self):
        card = MagicMock()
        card.id = 5
        player = MagicMock()
        player.hand = [card]
        engine = MagicMock()
        engine.get_player_by_id.return_value = player
        action = DiscardAction(player_id=1, card_ids=[5])
        result = action.execute(engine)
        assert result is True
        engine.discard_cards.assert_called_once()

    def test_execute_no_matching_cards(self):
        player = MagicMock()
        player.hand = []
        engine = MagicMock()
        engine.get_player_by_id.return_value = player
        action = DiscardAction(player_id=1, card_ids=[99])
        result = action.execute(engine)
        assert result is False

    def test_action_type(self):
        action = DiscardAction(player_id=1)
        assert action.action_type == ActionType.DISCARD
