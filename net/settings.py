"""Validated network runtime settings."""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from game.config import GameConfig
from net.security import (
    DEFAULT_HEARTBEAT_TIMEOUT,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_MAX_CONNECTIONS_PER_IP,
    DEFAULT_MAX_MESSAGE_SIZE,
)


class ServerSettings(BaseModel):
    """Validated server runtime settings."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8765, ge=1, le=65535)
    rate_limit_window: float = Field(default=1.0, gt=0)
    rate_limit_max_msgs: int = Field(default=30, gt=0)
    max_connections: int = Field(default=DEFAULT_MAX_CONNECTIONS, gt=0)
    max_connections_per_ip: int = Field(default=DEFAULT_MAX_CONNECTIONS_PER_IP, gt=0)
    max_message_size: int = Field(default=DEFAULT_MAX_MESSAGE_SIZE, gt=0)
    heartbeat_timeout: float = Field(default=DEFAULT_HEARTBEAT_TIMEOUT, gt=0)
    allowed_origins: str = ""
    allow_localhost_dev: bool = False
    ssl_cert: str = ""
    ssl_key: str = ""

    @field_validator("ssl_key")
    @classmethod
    def validate_tls_pair(cls, value: str, info) -> str:
        ssl_cert = info.data.get("ssl_cert", "")
        if bool(ssl_cert) != bool(value):
            raise ValueError(
                "ssl_cert and ssl_key must either both be set or both be empty",
            )
        return value

    @classmethod
    def from_config(
        cls,
        cfg: GameConfig,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> ServerSettings:
        """Build settings from the project runtime config."""
        return cls(
            host=host,
            port=port,
            rate_limit_window=cfg.ws_rate_limit_window,
            rate_limit_max_msgs=cfg.ws_rate_limit_max_msgs,
            max_connections=cfg.ws_max_connections,
            max_connections_per_ip=cfg.ws_max_connections_per_ip,
            max_message_size=cfg.ws_max_message_size,
            heartbeat_timeout=cfg.ws_heartbeat_timeout,
            allowed_origins=cfg.ws_allowed_origins,
            allow_localhost_dev=cfg.ws_dev_allow_localhost,
            ssl_cert=cfg.ws_ssl_cert,
            ssl_key=cfg.ws_ssl_key,
        )


class ClientSettings(BaseModel):
    """Validated client runtime settings."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    server_url: str
    auto_reconnect: bool = True
    reconnect_delay: float = Field(default=2.0, gt=0)
    max_reconnect_attempts: int = Field(default=5, gt=0)
    heartbeat_interval: float = Field(default=15.0, gt=0)

    @field_validator("server_url")
    @classmethod
    def validate_server_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError("server_url must use ws:// or wss://")
        if not parsed.hostname:
            raise ValueError("server_url must include a host")

        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("server_url port must be valid") from exc

        return value

    @classmethod
    def from_config(
        cls,
        cfg: GameConfig,
        *,
        server_url: str,
    ) -> ClientSettings:
        """Build settings from the project runtime config."""
        return cls(
            server_url=server_url,
            auto_reconnect=True,
            reconnect_delay=cfg.reconnect_delay,
            max_reconnect_attempts=cfg.max_reconnect_attempts,
            heartbeat_interval=cfg.heartbeat_interval,
        )
