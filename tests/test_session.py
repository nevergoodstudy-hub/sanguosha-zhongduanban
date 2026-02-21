"""Tests for net.session module."""

import time

from net.session import PlayerSession, SessionManager


class TestPlayerSession:
    def test_default_values(self):
        s = PlayerSession(player_id="p1")
        assert s.player_id == "p1"
        assert s.connected is True
        assert s.room_id is None
        assert s.game_seat is None
        assert len(s.token) > 20  # token_urlsafe(32) is ~43 chars

    def test_unique_tokens(self):
        s1 = PlayerSession(player_id="p1")
        s2 = PlayerSession(player_id="p2")
        assert s1.token != s2.token


class TestSessionManager:
    def test_create_session(self):
        mgr = SessionManager()
        s = mgr.create("player1", room_id="room_abc")
        assert s.player_id == "player1"
        assert s.room_id == "room_abc"
        assert s.connected is True
        assert mgr.active_count == 1

    def test_get_session(self):
        mgr = SessionManager()
        mgr.create("p1")
        assert mgr.get("p1") is not None
        assert mgr.get("p2") is None

    def test_reconnect_success(self):
        mgr = SessionManager(timeout=300)
        s = mgr.create("p1")
        token = s.token
        mgr.disconnect("p1")
        assert s.connected is False

        result = mgr.reconnect(token)
        assert result is not None
        assert result.connected is True
        assert result.player_id == "p1"

    def test_reconnect_bad_token(self):
        mgr = SessionManager()
        assert mgr.reconnect("invalid_token") is None

    def test_reconnect_expired(self):
        mgr = SessionManager(timeout=1.0)
        s = mgr.create("p1")
        token = s.token
        mgr.disconnect("p1")

        # Simulate timeout
        s.last_seen -= 2.0
        result = mgr.reconnect(token)
        assert result is None
        assert mgr.total_count == 0

    def test_disconnect_preserves_session(self):
        mgr = SessionManager()
        mgr.create("p1")
        mgr.disconnect("p1")
        assert mgr.total_count == 1
        assert mgr.active_count == 0

    def test_remove_session(self):
        mgr = SessionManager()
        s = mgr.create("p1")
        token = s.token
        mgr.remove("p1")
        assert mgr.total_count == 0
        assert mgr.reconnect(token) is None

    def test_create_replaces_old_session(self):
        mgr = SessionManager()
        s1 = mgr.create("p1")
        old_token = s1.token
        s2 = mgr.create("p1")
        assert s2.token != old_token
        assert mgr.total_count == 1
        assert mgr.reconnect(old_token) is None

    def test_cleanup_expired(self):
        mgr = SessionManager(timeout=1.0)
        s1 = mgr.create("p1")
        s2 = mgr.create("p2")
        mgr.disconnect("p1")
        mgr.disconnect("p2")

        # Only p1 expired
        s1.last_seen -= 2.0
        cleaned = mgr.cleanup_expired()
        assert cleaned == 1
        assert mgr.total_count == 1
        assert mgr.get("p1") is None
        assert mgr.get("p2") is not None

    def test_cleanup_skips_connected(self):
        mgr = SessionManager(timeout=0.01)
        s = mgr.create("p1")
        s.last_seen -= 1.0  # old but still connected
        cleaned = mgr.cleanup_expired()
        assert cleaned == 0
        assert mgr.total_count == 1

    def test_disconnect_nonexistent(self):
        mgr = SessionManager()
        mgr.disconnect("no_such_player")  # should not raise

    def test_remove_nonexistent(self):
        mgr = SessionManager()
        mgr.remove("no_such_player")  # should not raise
