"""Integration-style tests for the ``main.py --connect`` branch."""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

import main as main_module


class _FakeClientConfig:
    heartbeat_interval = 12.5
    reconnect_delay = 4.0
    max_reconnect_attempts = 7


def test_main_connect_normalizes_host_port_and_uses_default_name() -> None:
    with (
        patch("sys.argv", ["main.py", "--connect", " localhost:8765 "]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("game.config.get_config", return_value=_FakeClientConfig()),
        patch("net.client.cli_client_main") as mock_client_main,
        patch("asyncio.run") as mock_asyncio_run,
    ):
        main_module.main()

    mock_client_main.assert_called_once()
    assert mock_client_main.call_args.args == ("ws://localhost:8765", "玩家")
    settings = mock_client_main.call_args.kwargs["settings"]
    assert settings.server_url == "ws://localhost:8765"
    assert settings.reconnect_delay == 4.0
    assert settings.max_reconnect_attempts == 7
    assert settings.heartbeat_interval == 12.5
    called_coro = mock_asyncio_run.call_args.args[0]
    assert inspect.iscoroutine(called_coro)
    called_coro.close()


def test_main_connect_keeps_ws_url_and_uses_custom_name() -> None:
    with (
        patch("sys.argv", ["main.py", "--connect", "wss://game.example.com", "--name", "Alice"]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("game.config.get_config", return_value=_FakeClientConfig()),
        patch("net.client.cli_client_main") as mock_client_main,
        patch("asyncio.run") as mock_asyncio_run,
    ):
        main_module.main()

    mock_client_main.assert_called_once()
    assert mock_client_main.call_args.args == ("wss://game.example.com", "Alice")
    settings = mock_client_main.call_args.kwargs["settings"]
    assert settings.server_url == "wss://game.example.com"
    called_coro = mock_asyncio_run.call_args.args[0]
    assert inspect.iscoroutine(called_coro)
    called_coro.close()


@pytest.mark.parametrize(
    "bad_connect",
    [
        "   ",
        "http://example.com",
        "ws://:8765",
        "localhost:abc",
        "localhost:70000",
    ],
)
def test_main_connect_invalid_input_exits_before_client_start(
    capsys,
    bad_connect: str,
) -> None:
    with (
        patch("sys.argv", ["main.py", "--connect", bad_connect]),
        patch("main.setup_logging"),
        patch("main._warn_if_runtime_layout_suspicious"),
        patch("i18n.set_locale"),
        patch("net.client.cli_client_main") as mock_client_main,
        patch("asyncio.run") as mock_asyncio_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        main_module.main()

    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    assert "[ERROR] --connect 参数无效" in out
    mock_client_main.assert_not_called()
    mock_asyncio_run.assert_not_called()
