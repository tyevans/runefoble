"""Deterministic identifiers for the Soundscape aggregate (TASK-0576).

The aggregate id derives from the session id, so every process resolves the same event
stream for one session. A random id per process would start an empty stream on restart.
"""

from __future__ import annotations

from uuid import NAMESPACE_DNS, UUID, uuid5

SOUNDSCAPE_NAMESPACE: UUID = uuid5(NAMESPACE_DNS, "soundscape.runefoble")


def soundscape_aggregate_id(session_id: str) -> UUID:
    """Return the soundscape aggregate id for a session. The same session always maps to it."""
    return uuid5(SOUNDSCAPE_NAMESPACE, f"session:{session_id}")
