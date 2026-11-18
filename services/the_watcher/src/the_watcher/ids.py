"""Stream and aggregate identifiers for The Watcher."""

from __future__ import annotations

from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert a string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))
