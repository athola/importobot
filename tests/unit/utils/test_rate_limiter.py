"""Tests for rate limiter utility."""

from importobot.utils import rate_limiter


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_rate_limiter_enforces_time_window(monkeypatch):
    fake = FakeTime()
    monkeypatch.setattr(rate_limiter, "time", fake)

    limiter = rate_limiter.RateLimiter(max_calls=2, time_window=1.0)
    limiter.acquire()
    limiter.acquire()

    start = fake.now
    limiter.acquire()
    assert fake.now - start >= 1.0


def test_rate_limiter_reset(monkeypatch):
    fake = FakeTime()
    monkeypatch.setattr(rate_limiter, "time", fake)

    limiter = rate_limiter.RateLimiter(max_calls=1, time_window=1.0)
    limiter.acquire()
    limiter.reset()
    fake.now += 0.1
    limiter.acquire()
    assert fake.now == 0.1
