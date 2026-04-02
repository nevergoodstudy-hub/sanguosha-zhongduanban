"""Tests for server startup warning helpers in main.py."""

from unittest.mock import patch

from game.config import GameConfig
from main import _warn_for_network_security_defaults


def test_warn_network_defaults_reject_all_when_unconfigured(capsys) -> None:
    with patch.dict("os.environ", {}, clear=True):
        _warn_for_network_security_defaults()
    out = capsys.readouterr().out
    assert "SANGUOSHA_WS_ALLOWED_ORIGINS" in out
    assert "拒绝所有 WebSocket 连接" in out


def test_warn_network_defaults_dev_localhost_mode(capsys) -> None:
    with patch.dict(
        "os.environ",
        {
            "SANGUOSHA_DEV_ALLOW_LOCALHOST": "1",
        },
        clear=True,
    ):
        _warn_for_network_security_defaults()
    out = capsys.readouterr().out
    assert "SANGUOSHA_DEV_ALLOW_LOCALHOST" in out
    assert "localhost/127.0.0.1/::1" in out


def test_warn_network_defaults_silent_when_allowlist_set(capsys) -> None:
    with patch.dict(
        "os.environ",
        {
            "SANGUOSHA_WS_ALLOWED_ORIGINS": "http://localhost:3000",
        },
        clear=True,
    ):
        _warn_for_network_security_defaults()
    out = capsys.readouterr().out
    assert out == ""


def test_config_warning_matrix_no_warning_by_default() -> None:
    with patch.dict("os.environ", {}, clear=True):
        cfg = GameConfig.from_env()
    warnings = cfg.validate_warnings()
    assert warnings == []


def test_config_warning_matrix_dev_only() -> None:
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


def test_config_warning_matrix_dev_and_allowlist() -> None:
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
    assert any("SANGUOSHA_DEV_ALLOW_LOCALHOST" in w for w in warnings)
    assert any("SANGUOSHA_WS_ALLOWED_ORIGINS" in w for w in warnings)


def test_config_warning_matrix_allowlist_only() -> None:
    with patch.dict(
        "os.environ",
        {
            "SANGUOSHA_WS_ALLOWED_ORIGINS": "https://game.example.com",
        },
        clear=True,
    ):
        cfg = GameConfig.from_env()
    warnings = cfg.validate_warnings()
    assert warnings == []
