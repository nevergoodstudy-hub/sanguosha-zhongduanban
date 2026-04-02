"""Tests for main.normalize_connect_url."""

import pytest

from main import normalize_connect_url


def test_normalize_host_port_to_ws_url() -> None:
    assert normalize_connect_url("localhost:8765") == "ws://localhost:8765"


def test_normalize_ws_url_unchanged() -> None:
    assert normalize_connect_url("ws://localhost:8765") == "ws://localhost:8765"


def test_normalize_wss_url_unchanged() -> None:
    assert normalize_connect_url("wss://game.example.com") == "wss://game.example.com"


def test_normalize_trim_whitespace() -> None:
    assert normalize_connect_url("  localhost:9000  ") == "ws://localhost:9000"


def test_normalize_empty_raises_value_error() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        normalize_connect_url("   ")


def test_normalize_rejects_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="must start with ws:// or wss://"):
        normalize_connect_url("http://example.com")


def test_normalize_rejects_missing_host() -> None:
    with pytest.raises(ValueError, match="missing host"):
        normalize_connect_url("ws://:8765")


def test_normalize_rejects_non_numeric_port() -> None:
    with pytest.raises(ValueError, match="port must be numeric"):
        normalize_connect_url("localhost:abc")


def test_normalize_rejects_port_out_of_range() -> None:
    with pytest.raises(ValueError, match="port must be in 1-65535"):
        normalize_connect_url("localhost:70000")
