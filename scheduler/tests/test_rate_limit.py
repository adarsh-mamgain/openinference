"""Tests for the rate limiter and its behavior under burst load."""

import pytest

from inference_server.rate_limit import RateLimiter


def test_allows_under_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("key-a")
    assert limiter.allow("key-a")
    assert limiter.allow("key-a")
    assert limiter.remaining("key-a") == 0


def test_blocks_over_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("key") is True
    assert limiter.allow("key") is True
    assert limiter.allow("key") is False  # burst beyond the window limit


def test_limits_are_per_key():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("key-a")
    assert not limiter.allow("key-a")
    # A different key is unaffected.
    assert limiter.allow("key-b")
