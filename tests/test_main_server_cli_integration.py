"""Integration-style tests for main.py --server branch."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

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


def test_main_server_wires_gameserver_args_and_prints_warnings(capsys) -> None:
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

    fake_server_cls.assert_called_once_with(
        host="0.0.0.0",
        port=9001,
        rate_limit_window=fake_cfg.ws_rate_limit_window,
        rate_limit_max_msgs=fake_cfg.ws_rate_limit_max_msgs,
        max_connections=fake_cfg.ws_max_connections,
        max_connections_per_ip=fake_cfg.ws_max_connections_per_ip,
        max_message_size=fake_cfg.ws_max_message_size,
        heartbeat_timeout=fake_cfg.ws_heartbeat_timeout,
        allowed_origins=fake_cfg.ws_allowed_origins,
        allow_localhost_dev=fake_cfg.ws_dev_allow_localhost,
        ssl_cert=fake_cfg.ws_ssl_cert,
        ssl_key=fake_cfg.ws_ssl_key,
    )
    mock_asyncio_run.assert_called_once_with("START_CORO")


def test_main_server_config_error_exits_before_server_start(capsys) -> None:
    bad_cfg = types.SimpleNamespace(
        validate=lambda: ["websocket_port must be 1-65535"],
        validate_warnings=lambda: [],
    )

    with (
        patch("sys.argv", ["main.py", "--server"]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("game.config.get_config", return_value=bad_cfg),
        patch("net.server.GameServer") as mock_server_cls,
        patch("asyncio.run") as mock_asyncio_run,
    ):
        try:
            main_module.main()
            assert False, "expected SystemExit"
        except SystemExit as exc:
            assert exc.code == 2

    out = capsys.readouterr().out
    assert "[ERROR] 配置校验失败" in out
    assert "websocket_port must be 1-65535" in out
    mock_server_cls.assert_not_called()
    mock_asyncio_run.assert_not_called()
