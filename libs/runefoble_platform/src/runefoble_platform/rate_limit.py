"""Rate limit port and the in-process fixed-window limiter (ADR-0023 d).

A caller depends on `RateLimiter`, not on one implementation. A shared limiter (for example
Redis) can replace `FixedWindowRateLimiter` without a change to the caller. The in-process
limiter keeps its counts in memory, so each process counts only its own requests.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

# Above this many tracked keys, a hit also drops the expired windows.
SWEEP_THRESHOLD = 1024


@dataclass(frozen=True)
class RateDecision:
    """Whether a hit may proceed. `retry_after_seconds` is 0 when it may."""

    allowed: bool
    retry_after_seconds: int


class RateLimiter(Protocol):
    """Count one hit for `key` and say whether it is within the limit."""

    def hit(self, key: str) -> RateDecision: ...


@dataclass
class _Window:
    started: float
    count: int


class FixedWindowRateLimiter:
    """At most `limit` hits for each key in each window of `window_seconds`.

    A refused hit is not counted. The `Retry-After` value is the time to the end of the window.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1:
            raise ValueError("A rate limit needs at least one hit per window")
        if window_seconds <= 0:
            raise ValueError("A rate limit window must be longer than zero")
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._windows: dict[str, _Window] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> RateDecision:
        now = self._clock()
        with self._lock:
            if len(self._windows) >= SWEEP_THRESHOLD:
                self._drop_expired(now)
            window = self._windows.get(key)
            if window is None or self._expired(window, now):
                window = _Window(started=now, count=0)
                self._windows[key] = window
            if window.count >= self._limit:
                wait = math.ceil(window.started + self._window_seconds - now)
                return RateDecision(allowed=False, retry_after_seconds=max(wait, 1))
            window.count += 1
            return RateDecision(allowed=True, retry_after_seconds=0)

    def _expired(self, window: _Window, now: float) -> bool:
        return now - window.started >= self._window_seconds

    def _drop_expired(self, now: float) -> None:
        for key in [k for k, w in self._windows.items() if self._expired(w, now)]:
            del self._windows[key]


__all__ = ["FixedWindowRateLimiter", "RateDecision", "RateLimiter"]
