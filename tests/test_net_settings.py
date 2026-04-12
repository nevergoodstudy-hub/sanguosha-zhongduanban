"""Tests for validated network settings boundaries."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from game.config import GameConfig
from net.settings import ClientSettings, ServerSettings


def test_server_settings_from_config_maps_game_config_network_fields() -> None:
    cfg = GameConfig(
        ws_rate_limit_window=2.5,
        ws_rate_limit_max_msgs=41,
        ws_max_connections=321,
        ws_max_connections_per_ip=7,
        ws_max_message_size=70_000,
        ws_heartbeat_timeout=45.0,
        ws_allowed_origins="https://game.example.com",
        ws_dev_allow_localhost=True,
        ws_ssl_cert="cert.pem",
        ws_ssl_key="key.pem",
    )

    settings = ServerSettings.from_config(cfg, host="0.0.0.0", port=9001)

    assert settings.host == "0.0.0.0"
    assert settings.port == 9001
    assert settings.rate_limit_window == cfg.ws_rate_limit_window
    assert settings.rate_limit_max_msgs == cfg.ws_rate_limit_max_msgs
    assert settings.max_connections == cfg.ws_max_connections
    assert settings.max_connections_per_ip == cfg.ws_max_connections_per_ip
    assert settings.max_message_size == cfg.ws_max_message_size
    assert settings.heartbeat_timeout == cfg.ws_heartbeat_timeout
    assert settings.allowed_origins == cfg.ws_allowed_origins
    assert settings.allow_localhost_dev is True
    assert settings.ssl_cert == "cert.pem"
    assert settings.ssl_key == "key.pem"


def test_server_settings_requires_complete_tls_pair() -> None:
    with pytest.raises(ValidationError):
        ServerSettings(
            host="127.0.0.1",
            port=8765,
            ssl_cert="cert.pem",
            ssl_key="",
        )


def test_client_settings_from_config_maps_runtime_fields() -> None:
    cfg = GameConfig(
        heartbeat_interval=11.5,
        reconnect_delay=4.0,
        max_reconnect_attempts=8,
    )

    settings = ClientSettings.from_config(
        cfg,
        server_url="wss://game.example.com/socket",
    )

    assert settings.server_url == "wss://game.example.com/socket"
    assert settings.auto_reconnect is True
    assert settings.reconnect_delay == cfg.reconnect_delay
    assert settings.max_reconnect_attempts == cfg.max_reconnect_attempts
    assert settings.heartbeat_interval == cfg.heartbeat_interval


def test_client_settings_rejects_non_websocket_url() -> None:
    with pytest.raises(ValidationError):
        ClientSettings(server_url="https://game.example.com")
