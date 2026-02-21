"""Tests for net.rate_limiter module."""

import time
from unittest.mock import patch

from net.rate_limiter import ConnectionRateLimiter, TokenBucket


class TestTokenBucket:
    def test_initial_burst_allowed(self):
        bucket = TokenBucket(rate=10.0, burst=5)
        # Should allow up to burst count
        for _ in range(5):
            assert bucket.consume() is True
        # 6th should fail
        assert bucket.consume() is False

    def test_refill_over_time(self):
        bucket = TokenBucket(rate=10.0, burst=5)
        # Exhaust all tokens
        for _ in range(5):
            bucket.consume()

        # Simulate 0.5 seconds passing (5 tokens refilled)
        bucket.last_refill -= 0.5
        assert bucket.consume() is True

    def test_consume_multiple(self):
        bucket = TokenBucket(rate=10.0, burst=10)
        assert bucket.consume(5) is True
        assert bucket.consume(5) is True
        assert bucket.consume(1) is False

    def test_burst_cap(self):
        bucket = TokenBucket(rate=100.0, burst=5)
        # Even after long time, tokens capped at burst
        bucket.last_refill -= 100  # simulate 100 seconds
        assert bucket.consume(5) is True
        assert bucket.consume(1) is False

    def test_available_property(self):
        bucket = TokenBucket(rate=10.0, burst=20)
        assert bucket.available == 20.0
        bucket.consume(10)
        # available should be ~10 (maybe slightly more due to tiny elapsed time)
        assert 9.9 <= bucket.available <= 10.1

    def test_zero_rate(self):
        bucket = TokenBucket(rate=0.0, burst=3)
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is True
        assert bucket.consume() is False
        # No refill happens with rate=0
        bucket.last_refill -= 10
        assert bucket.consume() is False


class TestConnectionRateLimiter:
    def test_independent_connections(self):
        limiter = ConnectionRateLimiter(rate=10.0, burst=2)
        assert limiter.check("conn_a") is True
        assert limiter.check("conn_a") is True
        assert limiter.check("conn_a") is False
        # Different connection should have its own bucket
        assert limiter.check("conn_b") is True

    def test_remove_connection(self):
        limiter = ConnectionRateLimiter(rate=10.0, burst=1)
        assert limiter.check("conn_a") is True
        assert limiter.check("conn_a") is False
        limiter.remove("conn_a")
        # After removal, should get a fresh bucket
        assert limiter.check("conn_a") is True

    def test_remove_nonexistent(self):
        limiter = ConnectionRateLimiter()
        limiter.remove("no_such_conn")  # should not raise

    def test_active_connections(self):
        limiter = ConnectionRateLimiter()
        assert limiter.active_connections == 0
        limiter.check("a")
        limiter.check("b")
        assert limiter.active_connections == 2
        limiter.remove("a")
        assert limiter.active_connections == 1
