"""Poll a condition until it holds or a time limit passes."""

from __future__ import annotations

import time
from collections.abc import Callable


def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout_s: float,
    interval_s: float = 0.2,
) -> bool:
    """Call `predicate` until it returns True or `timeout_s` seconds pass.

    The predicate runs at least once. Return True when it held, False when the time limit passed.
    The caller decides whether a False result is a failure and what message to raise.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval_s)
