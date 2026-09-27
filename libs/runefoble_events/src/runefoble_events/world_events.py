"""Backwards-compatibility alias for runefoble_events.events.world_events."""

# ruff: noqa: F403

from runefoble_events.events import world_events
from runefoble_events.events.world_events import *

__all__ = list(world_events.__all__)
