"""Tests for main.normalize_connect_url."""

from main import normalize_connect_url


def test_normalize_host_port_to_ws_url() -> None:
    assert normalize_connect_url("localhost:8765") == "ws://localhost:8765"


def test_normalize_ws_url_unchanged() -> None:
    assert normalize_connect_url("ws://localhost:8765") == "ws://localhost:8765"


def test_normalize_wss_url_unchanged() -> None:
    assert normalize_connect_url("wss://game.example.com") == "wss://game.example.com"


def test_normalize_trim_whitespace() -> None:
    assert normalize_connect_url("  localhost:9000  ") == "ws://localhost:9000"
