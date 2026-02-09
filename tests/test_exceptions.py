"""Tests for game.exceptions module — all exception classes and helpers."""

import pytest

from game.exceptions import (
    CardNotFoundError,
    ConfigurationError,
    DataLoadError,
    GameAlreadyFinishedError,
    GameError,
    GameNotStartedError,
    GameStateError,
    InsufficientCardsError,
    InvalidActionError,
    InvalidPhaseError,
    InvalidTargetError,
    NotPlayerTurnError,
    PlayerDeadError,
    PlayerError,
    PlayerNotFoundError,
    SkillConditionError,
    SkillCooldownError,
    SkillError,
    SkillNotFoundError,
    SkillUsageLimitError,
    raise_if_game_finished,
    raise_if_game_not_started,
    raise_if_player_dead,
)

# ==================== GameError base ====================

class TestGameError:
    def test_basic(self):
        e = GameError("test")
        assert e.message == "test"
        assert e.details == {}
        assert str(e) == "test"

    def test_with_details(self):
        e = GameError("err", details={"key": "val"})
        assert e.details == {"key": "val"}
        assert "Details:" in str(e)

    def test_is_exception(self):
        with pytest.raises(GameError):
            raise GameError("boom")


# ==================== Action errors ====================

class TestInvalidActionError:
    def test_defaults(self):
        e = InvalidActionError()
        assert "无效" in e.message
        assert e.action_type is None
        assert e.player_id is None
        assert e.details == {}

    def test_with_params(self):
        e = InvalidActionError("bad", action_type="play", player_id=1)
        assert e.action_type == "play"
        assert e.player_id == 1
        assert e.details["action_type"] == "play"
        assert e.details["player_id"] == 1

    def test_inherits_game_error(self):
        assert issubclass(InvalidActionError, GameError)


class TestInvalidTargetError:
    def test_defaults(self):
        e = InvalidTargetError()
        assert e.target_ids is None
        assert e.reason is None

    def test_with_params(self):
        e = InvalidTargetError("bad target", target_ids=[1, 2], reason="dead")
        assert e.target_ids == [1, 2]
        assert e.reason == "dead"
        assert e.details["target_ids"] == [1, 2]
        assert e.details["reason"] == "dead"


class TestInsufficientCardsError:
    def test_defaults(self):
        e = InsufficientCardsError()
        assert e.required == 0
        assert e.available == 0
        assert e.card_type is None

    def test_with_params(self):
        e = InsufficientCardsError("no cards", required=3, available=1, card_type="sha")
        assert e.required == 3
        assert e.available == 1
        assert e.card_type == "sha"
        assert e.details["card_type"] == "sha"

    def test_without_card_type(self):
        e = InsufficientCardsError(required=2, available=0)
        assert "card_type" not in e.details


class TestCardNotFoundError:
    def test_defaults(self):
        e = CardNotFoundError()
        assert e.card_id is None

    def test_with_card_id(self):
        e = CardNotFoundError(card_id="sha_01")
        assert e.card_id == "sha_01"
        assert e.details["card_id"] == "sha_01"


# ==================== Skill errors ====================

class TestSkillError:
    def test_defaults(self):
        e = SkillError()
        assert e.skill_id is None
        assert e.player_id is None

    def test_with_params(self):
        e = SkillError("err", skill_id="wusheng", player_id=2)
        assert e.skill_id == "wusheng"
        assert e.player_id == 2

    def test_inherits_game_error(self):
        assert issubclass(SkillError, GameError)


class TestSkillNotFoundError:
    def test_defaults(self):
        e = SkillNotFoundError()
        assert isinstance(e, SkillError)

    def test_with_params(self):
        e = SkillNotFoundError(skill_id="rende", player_id=3)
        assert e.skill_id == "rende"


class TestSkillCooldownError:
    def test_defaults(self):
        e = SkillCooldownError()
        assert e.remaining_cooldown == 0

    def test_with_cooldown(self):
        e = SkillCooldownError(remaining_cooldown=3)
        assert e.remaining_cooldown == 3
        assert e.details["remaining_cooldown"] == 3


class TestSkillConditionError:
    def test_defaults(self):
        e = SkillConditionError()
        assert e.condition is None

    def test_with_condition(self):
        e = SkillConditionError(condition="need_black_card")
        assert e.condition == "need_black_card"
        assert e.details["condition"] == "need_black_card"


class TestSkillUsageLimitError:
    def test_defaults(self):
        e = SkillUsageLimitError()
        assert e.limit == 0
        assert e.used == 0

    def test_with_params(self):
        e = SkillUsageLimitError(limit=1, used=1)
        assert e.limit == 1
        assert e.used == 1
        assert e.details["limit"] == 1
        assert e.details["used"] == 1


# ==================== Game state errors ====================

class TestGameStateError:
    def test_defaults(self):
        e = GameStateError()
        assert e.current_state is None
        assert e.expected_state is None

    def test_with_states(self):
        e = GameStateError("bad state", current_state="playing", expected_state="setup")
        assert e.current_state == "playing"
        assert e.expected_state == "setup"
        assert e.details["current_state"] == "playing"


class TestGameNotStartedError:
    def test_default(self):
        e = GameNotStartedError()
        assert e.current_state == "not_started"
        assert isinstance(e, GameStateError)

    def test_custom_message(self):
        e = GameNotStartedError("game hasn't begun")
        assert e.message == "game hasn't begun"


class TestGameAlreadyFinishedError:
    def test_default(self):
        e = GameAlreadyFinishedError()
        assert e.current_state == "finished"
        assert isinstance(e, GameStateError)


class TestInvalidPhaseError:
    def test_defaults(self):
        e = InvalidPhaseError()
        assert e.current_phase is None
        assert e.expected_phase is None

    def test_with_phases(self):
        e = InvalidPhaseError(current_phase="discard", expected_phase="play")
        assert e.current_phase == "discard"
        assert e.expected_phase == "play"


# ==================== Player errors ====================

class TestPlayerError:
    def test_defaults(self):
        e = PlayerError()
        assert e.player_id is None

    def test_with_player_id(self):
        e = PlayerError(player_id=5)
        assert e.player_id == 5
        assert e.details["player_id"] == 5


class TestPlayerNotFoundError:
    def test_default(self):
        e = PlayerNotFoundError()
        assert isinstance(e, PlayerError)

    def test_with_id(self):
        e = PlayerNotFoundError(player_id=99)
        assert e.player_id == 99


class TestPlayerDeadError:
    def test_default(self):
        e = PlayerDeadError()
        assert isinstance(e, PlayerError)

    def test_with_id(self):
        e = PlayerDeadError(player_id=3)
        assert e.player_id == 3


class TestNotPlayerTurnError:
    def test_defaults(self):
        e = NotPlayerTurnError()
        assert e.current_player_id is None

    def test_with_ids(self):
        e = NotPlayerTurnError(player_id=2, current_player_id=1)
        assert e.player_id == 2
        assert e.current_player_id == 1
        assert e.details["current_player_id"] == 1


# ==================== Config/Data errors ====================

class TestConfigurationError:
    def test_defaults(self):
        e = ConfigurationError()
        assert e.config_key is None

    def test_with_key(self):
        e = ConfigurationError(config_key="max_players")
        assert e.config_key == "max_players"
        assert e.details["config_key"] == "max_players"


class TestDataLoadError:
    def test_defaults(self):
        e = DataLoadError()
        assert e.file_path is None
        assert e.reason is None

    def test_with_params(self):
        e = DataLoadError(file_path="/data/heroes.json", reason="not found")
        assert e.file_path == "/data/heroes.json"
        assert e.reason == "not found"
        assert e.details["file_path"] == "/data/heroes.json"
        assert e.details["reason"] == "not found"


# ==================== Helper functions ====================

class TestHelperFunctions:
    def test_raise_if_game_not_started_raises(self):
        with pytest.raises(GameNotStartedError):
            raise_if_game_not_started("not_started")

    def test_raise_if_game_not_started_ok(self):
        raise_if_game_not_started("playing")  # should not raise

    def test_raise_if_game_finished_raises(self):
        with pytest.raises(GameAlreadyFinishedError):
            raise_if_game_finished("finished")

    def test_raise_if_game_finished_ok(self):
        raise_if_game_finished("playing")  # should not raise

    def test_raise_if_player_dead_raises(self):
        with pytest.raises(PlayerDeadError):
            raise_if_player_dead(True, player_id=1)

    def test_raise_if_player_dead_ok(self):
        raise_if_player_dead(False)  # should not raise

    def test_raise_if_player_dead_no_id(self):
        with pytest.raises(PlayerDeadError) as exc_info:
            raise_if_player_dead(True)
        assert exc_info.value.player_id is None
