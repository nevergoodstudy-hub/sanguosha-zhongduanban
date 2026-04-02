"""Tests for non-blocking config warning validation."""

from unittest.mock import patch

from game.config import GameConfig


def test_validate_warnings_empty_by_default() -> None:
    with patch.dict("os.environ", {}, clear=True):
        cfg = GameConfig.from_env()
    assert cfg.validate_warnings() == []


def test_validate_warnings_for_dev_localhost_only() -> None:
    with patch.dict(
        "os.environ",
        {
            "SANGUOSHA_DEV_ALLOW_LOCALHOST": "1",
        },
        clear=True,
    ):
        cfg = GameConfig.from_env()
    warnings = cfg.validate_warnings()
    assert any("SANGUOSHA_DEV_ALLOW_LOCALHOST" in w for w in warnings)


def test_validate_warnings_for_dev_localhost_plus_allowlist() -> None:
    with patch.dict(
        "os.environ",
        {
            "SANGUOSHA_DEV_ALLOW_LOCALHOST": "1",
            "SANGUOSHA_WS_ALLOWED_ORIGINS": "https://game.example.com",
        },
        clear=True,
    ):
        cfg = GameConfig.from_env()
    warnings = cfg.validate_warnings()
    assert len(warnings) >= 2
    assert any("SANGUOSHA_DEV_ALLOW_LOCALHOST" in w for w in warnings)
    assert any("SANGUOSHA_WS_ALLOWED_ORIGINS" in w for w in warnings)
