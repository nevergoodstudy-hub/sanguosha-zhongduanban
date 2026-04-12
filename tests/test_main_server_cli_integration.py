"""Integration-style tests for the ``main.py --server`` branch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import main as main_module


class _FakeConfig:
    ws_rate_limit_window = 1.5
    ws_rate_limit_max_msgs = 42
    ws_max_connections = 321
    ws_max_connections_per_ip = 12
    ws_max_message_size = 77777
    ws_heartbeat_timeout = 33.0
    ws_allowed_origins = "https://game.example.com"
    ws_dev_allow_localhost = True
    ws_ssl_cert = "cert.pem"
    ws_ssl_key = "key.pem"

    def validate(self) -> list[str]:
        return []

    def validate_warnings(self) -> list[str]:
        return ["dev localhost enabled for testing"]


def test_main_server_wires_gameserver_settings_and_prints_warnings(capsys) -> None:
    fake_cfg = _FakeConfig()

    fake_server_instance = MagicMock()
    fake_server_instance.start = MagicMock(return_value="START_CORO")
    fake_server_cls = MagicMock(return_value=fake_server_instance)

    with (
        patch("sys.argv", ["main.py", "--server", "0.0.0.0:9001"]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("game.config.get_config", return_value=fake_cfg),
        patch("net.server.GameServer", fake_server_cls),
        patch("asyncio.run") as mock_asyncio_run,
    ):
        main_module.main()

    out = capsys.readouterr().out
    assert "[WARN] dev localhost enabled for testing" in out

    fake_server_cls.assert_called_once()
    settings = fake_server_cls.call_args.kwargs["settings"]
    assert settings.host == "0.0.0.0"
    assert settings.port == 9001
    assert settings.rate_limit_window == fake_cfg.ws_rate_limit_window
    assert settings.rate_limit_max_msgs == fake_cfg.ws_rate_limit_max_msgs
    assert settings.max_connections == fake_cfg.ws_max_connections
    assert settings.max_connections_per_ip == fake_cfg.ws_max_connections_per_ip
    assert settings.max_message_size == fake_cfg.ws_max_message_size
    assert settings.heartbeat_timeout == fake_cfg.ws_heartbeat_timeout
    assert settings.allowed_origins == fake_cfg.ws_allowed_origins
    assert settings.allow_localhost_dev == fake_cfg.ws_dev_allow_localhost
    assert settings.ssl_cert == fake_cfg.ws_ssl_cert
    assert settings.ssl_key == fake_cfg.ws_ssl_key
    mock_asyncio_run.assert_called_once_with("START_CORO")


def test_main_server_config_error_exits_before_server_start(capsys) -> None:
    class _BadConfig:
        ws_rate_limit_window = 1.0
        ws_rate_limit_max_msgs = 30
        ws_max_connections = 100
        ws_max_connections_per_ip = 4
        ws_max_message_size = 65536
        ws_heartbeat_timeout = 60.0
        ws_allowed_origins = ""
        ws_dev_allow_localhost = False
        ws_ssl_cert = ""
        ws_ssl_key = ""

        def validate(self) -> list[str]:
            return ["websocket_port must be 1-65535"]

        def validate_warnings(self) -> list[str]:
            return []

    bad_cfg = _BadConfig()

    with (
        patch("sys.argv", ["main.py", "--server"]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("game.config.get_config", return_value=bad_cfg),
        patch("net.server.GameServer") as mock_server_cls,
        patch("asyncio.run") as mock_asyncio_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        main_module.main()

    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    assert "[ERROR] 配置校验失败:" in out
    assert "websocket_port must be 1-65535" in out
    mock_server_cls.assert_not_called()
    mock_asyncio_run.assert_not_called()


def test_main_server_settings_validation_error_exits_before_server_start(capsys) -> None:
    class _TlsConfig:
        ws_rate_limit_window = 1.0
        ws_rate_limit_max_msgs = 30
        ws_max_connections = 100
        ws_max_connections_per_ip = 4
        ws_max_message_size = 65536
        ws_heartbeat_timeout = 60.0
        ws_allowed_origins = "https://game.example.com"
        ws_dev_allow_localhost = False
        ws_ssl_cert = "cert.pem"
        ws_ssl_key = ""

        def validate(self) -> list[str]:
            return []

        def validate_warnings(self) -> list[str]:
            return []

    tls_cfg = _TlsConfig()

    with (
        patch("sys.argv", ["main.py", "--server"]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("game.config.get_config", return_value=tls_cfg),
        patch("net.server.GameServer") as mock_server_cls,
        patch("asyncio.run") as mock_asyncio_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        main_module.main()

    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    assert "[ERROR] 配置校验失败:" in out
    assert "ssl_cert" in out
    assert "ssl_key" in out
    mock_server_cls.assert_not_called()
    mock_asyncio_run.assert_not_called()
