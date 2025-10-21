"""Simple thread-safe token bucket rate limiter."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock


class RateLimiter:
    """Token bucket rate limiter for API clients."""

    def __init__(self, max_calls: int, time_window: float) -> None:
        """Create a rate limiter with the given call budget and time window."""
        if max_calls <= 0:
            raise ValueError("max_calls must be positive")
        if time_window <= 0:
            raise ValueError("time_window must be positive")

        self.max_calls = max_calls
        self.time_window = time_window
        self._timestamps: deque[float] = deque()
        self._lock = Lock()

    def acquire(self) -> None:
        """Block until a permit is available inside the time window."""
        sleep_time = 0.0
        with self._lock:
            now = time.time()
            window_start = now - self.time_window

            while self._timestamps and self._timestamps[0] < window_start:
                self._timestamps.popleft()

            if len(self._timestamps) < self.max_calls:
                self._timestamps.append(now)
                return

            sleep_time = max(self.time_window - (now - self._timestamps[0]), 0.0)

        if sleep_time > 0:
            time.sleep(sleep_time)

        with self._lock:
            self._timestamps.append(time.time())

    def reset(self) -> None:
        """Reset rate limiter state (useful for tests)."""
        with self._lock:
            self._timestamps.clear()
