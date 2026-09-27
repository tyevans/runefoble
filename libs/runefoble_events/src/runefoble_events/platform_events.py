"""Backwards-compatibility alias for runefoble_events.events.platform_events."""

# ruff: noqa: F403

from runefoble_events.events import platform_events
from runefoble_events.events.platform_events import *

__all__ = list(platform_events.__all__)
