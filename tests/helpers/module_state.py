"""Restore a module-level seam to the value it held before a test.

A seam is a process global with a getter and a setter. A test that sets a seam must put back
the previous value, not `None` and not a fresh object. Setting `None` lets the next getter
build a real client or store, so a later test can reach a real endpoint.

Use `restored_seam` in a `with` block, or the `seam_restorer` fixture when a fixture sets
several seams and restores them at teardown in reverse order.

Governed by ADR-0014 and ADR-0015 (TASK-0714).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest

SeamGetter = Callable[[], Any]
SeamSetter = Callable[[Any], None]


@contextmanager
def restored_seam(
    get: SeamGetter, set_: SeamSetter, value: Any = None, *, replace: bool = False
) -> Iterator[Any]:
    """Save the previous seam value, optionally set `value`, then restore the previous value.

    With `replace=False` the seam keeps its value and only the restore runs at exit.
    With `replace=True` the seam holds `value` inside the block. Yields the previous value.
    """
    previous = get()
    if replace:
        set_(value)
    try:
        yield previous
    finally:
        set_(previous)


class SeamRestorer:
    """Record seam values set by a fixture, and restore each previous value at teardown."""

    def __init__(self) -> None:
        self._restores: list[tuple[SeamSetter, Any]] = []

    def keep(self, get: SeamGetter, set_: SeamSetter) -> None:
        """Record the seam value now, and put it back at teardown. The seam is not changed."""
        self._restores.append((set_, get()))

    def replace(self, get: SeamGetter, set_: SeamSetter, value: Any) -> Any:
        """Set `value` on the seam now. Teardown puts the value from before this call back."""
        self.keep(get, set_)
        set_(value)
        return value

    def restore(self) -> None:
        """Put back every recorded previous value, newest first."""
        while self._restores:
            set_, previous = self._restores.pop()
            set_(previous)


@pytest.fixture
def seam_restorer() -> Iterator[SeamRestorer]:
    """Yield a `SeamRestorer` and restore every seam it recorded when the test ends."""
    restorer = SeamRestorer()
    try:
        yield restorer
    finally:
        restorer.restore()
