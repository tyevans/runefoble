"""Backwards-compatibility alias for runefoble_events.events.media_events."""

# ruff: noqa: F403

from runefoble_events.events import media_events
from runefoble_events.events.media_events import *

__all__ = list(media_events.__all__)
