"""Redis stream names that the game session domains publish to (ADR-0021 D2).

The names do not change during the package migration (ADR-0021 D5).
"""

from __future__ import annotations

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_SESSION = "runefoble.events.session"
STREAM_STRONGHOLD = "runefoble.events.stronghold"
STREAM_TAVERN = "runefoble.events.tavern"
STREAM_WEST_MARCHES = "runefoble.events.west_marches"

__all__ = [
    "STREAM_SESSION",
    "STREAM_STRONGHOLD",
    "STREAM_TAVERN",
    "STREAM_WATCHER",
    "STREAM_WEST_MARCHES",
]
