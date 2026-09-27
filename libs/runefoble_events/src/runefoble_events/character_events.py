"""Backwards-compatibility alias for runefoble_events.events.character_events."""

# ruff: noqa: F403

from runefoble_events.events import character_events
from runefoble_events.events.character_events import *

__all__ = list(character_events.__all__)
