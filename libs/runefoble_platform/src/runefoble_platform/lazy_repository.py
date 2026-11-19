"""A lazily built aggregate repository with one replaceable seam (SVC-07, TASK-0819).

A service holds one `LazyRepository` per aggregate type at module level. It builds the
repository on first use and keeps it. Tests replace it with `set` and reset it with `set(None)`.
"""

from __future__ import annotations

from collections.abc import Callable

from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.aggregate import DeclarativeAggregate


class LazyRepository[T: DeclarativeAggregate]:
    """Own one aggregate repository. Build it through `factory` on the first `get`."""

    def __init__(self, factory: Callable[[], AggregateRepository[T]]) -> None:
        self._factory = factory
        self._repo: AggregateRepository[T] | None = None

    def get(self) -> AggregateRepository[T]:
        """Return the repository. Build it on first use."""
        if self._repo is None:
            self._repo = self._factory()
        return self._repo

    def set(self, repo: AggregateRepository[T] | None) -> None:
        """Replace the repository. None resets it, so the next `get` builds one again."""
        self._repo = repo


__all__ = ["LazyRepository"]
