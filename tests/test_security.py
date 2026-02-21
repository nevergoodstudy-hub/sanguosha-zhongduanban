"""Tests for net/security.py — token manager, origin validation, rate limiter, sanitization."""

import time

from net.security import (
    ConnectionTokenManager,
    IPConnectionTracker,
    OriginValidator,
    RateLimiter,
    sanitize_chat_message,
)

# ==================== ConnectionTokenManager ====================


class TestConnectionTokenManager:
    def test_issue_and_verify(self):
        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=1)
        assert isinstance(token, str)
        assert len(token) > 0
        assert mgr.verify(token, expected_player_id=1) is True

    def test_verify_wrong_player(self):
        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=1)
        assert mgr.verify(token, expected_player_id=2) is False

    def test_verify_invalid_token(self):
        mgr = ConnectionTokenManager()
        mgr.issue(player_id=1)
        assert mgr.verify("invalid_token_abc", expected_player_id=1) is False

    def test_revoke_by_player_id(self):
        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=5)
        mgr.revoke(player_id=5)
        assert mgr.verify(token, expected_player_id=5) is False

    def test_revoke_by_token(self):
        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=3)
        mgr.revoke(token=token)
        assert mgr.verify(token, expected_player_id=3) is False

    def test_issue_replaces_old_token(self):
        mgr = ConnectionTokenManager()
        old = mgr.issue(player_id=1)
        new = mgr.issue(player_id=1)
        assert old != new
        assert mgr.verify(old, expected_player_id=1) is False
        assert mgr.verify(new, expected_player_id=1) is True

    def test_expired_token(self):
        mgr = ConnectionTokenManager(expiry=0.01)
        token = mgr.issue(player_id=1)
        time.sleep(0.05)
        assert mgr.verify(token, expected_player_id=1) is False

    def test_cleanup_expired(self):
        mgr = ConnectionTokenManager(expiry=0.01)
        mgr.issue(player_id=1)
        mgr.issue(player_id=2)
        time.sleep(0.05)
        cleaned = mgr.cleanup_expired()
        assert cleaned == 2
        assert mgr.active_count == 0

    def test_active_count(self):
        mgr = ConnectionTokenManager()
        assert mgr.active_count == 0
        mgr.issue(player_id=1)
        mgr.issue(player_id=2)
        assert mgr.active_count == 2
        mgr.revoke(player_id=1)
        assert mgr.active_count == 1


# ==================== OriginValidator ====================


class TestOriginValidator:
    def test_empty_denies_all(self):
        """P0-3: Empty whitelist = fail-closed (deny all), not fail-open."""
        v = OriginValidator("")
        assert v.is_enabled is False
        assert v.is_allowed("http://evil.com") is False
        assert v.is_allowed(None) is False

    def test_whitelist_allows_valid(self):
        v = OriginValidator("http://localhost:8080, https://example.com")
        assert v.is_enabled is True
        assert v.is_allowed("http://localhost:8080") is True
        assert v.is_allowed("https://example.com") is True

    def test_whitelist_blocks_invalid(self):
        v = OriginValidator("http://localhost:8080")
        assert v.is_allowed("http://evil.com") is False

    def test_whitelist_blocks_none(self):
        v = OriginValidator("http://localhost:8080")
        assert v.is_allowed(None) is False

    def test_case_insensitive(self):
        v = OriginValidator("HTTP://EXAMPLE.COM")
        assert v.is_allowed("http://example.com") is True

    def test_trailing_slash_ignored(self):
        v = OriginValidator("http://example.com/")
        assert v.is_allowed("http://example.com") is True

    def test_allowed_origins_export_sorted(self):
        v = OriginValidator("https://b.example, https://a.example")
        assert v.allowed_origins == ("https://a.example", "https://b.example")


# ==================== RateLimiter ====================


class TestRateLimiter:
    def test_allows_under_limit(self):
        rl = RateLimiter(window=1.0, max_msgs=5)
        for _ in range(5):
            assert rl.check(player_id=1) is True

    def test_blocks_over_limit(self):
        rl = RateLimiter(window=1.0, max_msgs=3)
        for _ in range(3):
            rl.check(player_id=1)
        assert rl.check(player_id=1) is False

    def test_separate_players(self):
        rl = RateLimiter(window=1.0, max_msgs=2)
        rl.check(player_id=1)
        rl.check(player_id=1)
        assert rl.check(player_id=1) is False
        # Player 2 is independent
        assert rl.check(player_id=2) is True

    def test_window_expiry(self):
        rl = RateLimiter(window=0.05, max_msgs=2)
        rl.check(player_id=1)
        rl.check(player_id=1)
        assert rl.check(player_id=1) is False
        time.sleep(0.1)
        assert rl.check(player_id=1) is True

    def test_remove_player(self):
        rl = RateLimiter(window=1.0, max_msgs=2)
        rl.check(player_id=1)
        rl.check(player_id=1)
        rl.remove_player(player_id=1)
        assert rl.check(player_id=1) is True


# ==================== sanitize_chat_message ====================


class TestSanitizeChatMessage:
    def test_normal_text(self):
        assert sanitize_chat_message("hello") == "hello"

    def test_html_escape(self):
        result = sanitize_chat_message("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;" in result

    def test_max_length(self):
        result = sanitize_chat_message("a" * 1000, max_length=50)
        assert len(result) <= 50

    def test_strips_whitespace(self):
        assert sanitize_chat_message("  hello  ") == "hello"

    def test_empty_string(self):
        assert sanitize_chat_message("") == ""


# ==================== IPConnectionTracker ====================


class TestIPConnectionTracker:
    def test_initial_can_connect(self):
        tracker = IPConnectionTracker(max_per_ip=3)
        assert tracker.can_connect("1.2.3.4") is True

    def test_blocks_at_limit(self):
        tracker = IPConnectionTracker(max_per_ip=2)
        tracker.add("1.2.3.4")
        tracker.add("1.2.3.4")
        assert tracker.can_connect("1.2.3.4") is False

    def test_remove_frees_slot(self):
        tracker = IPConnectionTracker(max_per_ip=1)
        tracker.add("1.2.3.4")
        assert tracker.can_connect("1.2.3.4") is False
        tracker.remove("1.2.3.4")
        assert tracker.can_connect("1.2.3.4") is True

    def test_get_count(self):
        tracker = IPConnectionTracker()
        assert tracker.get_count("5.6.7.8") == 0
        tracker.add("5.6.7.8")
        assert tracker.get_count("5.6.7.8") == 1

    def test_remove_nonexistent_ip(self):
        tracker = IPConnectionTracker()
        tracker.remove("9.9.9.9")  # should not raise
        assert tracker.get_count("9.9.9.9") == 0
