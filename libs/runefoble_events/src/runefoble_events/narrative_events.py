"""Backwards-compatibility alias for runefoble_events.events.narrative_events."""

# ruff: noqa: F403

from runefoble_events.events import narrative_events
from runefoble_events.events.narrative_events import *

__all__ = list(narrative_events.__all__)
