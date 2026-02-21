"""Configuration validation tests (P2-5)."""

import pytest

from game.config import GameConfig


class TestConfigValidation:
    """Test GameConfig.validate()."""

    def test_default_config_valid(self):
        """Default config should pass validation."""
        cfg = GameConfig()
        errors = cfg.validate()
        assert errors == [], f"Default config errors: {errors}"

    def test_invalid_min_players(self):
        cfg = GameConfig(min_players=1)
        errors = cfg.validate()
        assert any("min_players" in e for e in errors)

    def test_invalid_max_players(self):
        cfg = GameConfig(max_players=20)
        errors = cfg.validate()
        assert any("max_players" in e for e in errors)

    def test_min_greater_than_max_players(self):
        cfg = GameConfig(min_players=6, max_players=4)
        errors = cfg.validate()
        assert any("min_players" in e and "max_players" in e for e in errors)

    def test_invalid_port_zero(self):
        cfg = GameConfig(websocket_port=0)
        errors = cfg.validate()
        assert any("websocket_port" in e for e in errors)

    def test_invalid_port_too_large(self):
        cfg = GameConfig(websocket_port=70000)
        errors = cfg.validate()
        assert any("websocket_port" in e for e in errors)

    def test_negative_ai_delay(self):
        cfg = GameConfig(ai_turn_delay=-1.0)
        errors = cfg.validate()
        assert any("ai_turn_delay" in e for e in errors)

    def test_zero_ai_delay_valid(self):
        """Zero delay is valid (disabled)."""
        cfg = GameConfig(ai_turn_delay=0.0)
        errors = cfg.validate()
        assert not any("ai_turn_delay" in e for e in errors)

    def test_zero_timeout_invalid(self):
        cfg = GameConfig(play_phase_timeout=0)
        errors = cfg.validate()
        assert any("play_phase_timeout" in e for e in errors)

    def test_zero_max_connections_invalid(self):
        cfg = GameConfig(ws_max_connections=0)
        errors = cfg.validate()
        assert any("ws_max_connections" in e for e in errors)

    def test_zero_initial_hand_size_invalid(self):
        cfg = GameConfig(initial_hand_size=0)
        errors = cfg.validate()
        assert any("initial_hand_size" in e for e in errors)

    def test_multiple_errors_at_once(self):
        """Multiple invalid values produce multiple errors."""
        cfg = GameConfig(min_players=0, websocket_port=0, ai_max_actions=0)
        errors = cfg.validate()
        assert len(errors) >= 3
