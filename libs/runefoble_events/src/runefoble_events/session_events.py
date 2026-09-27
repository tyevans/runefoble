"""Backwards-compatibility alias for runefoble_events.events.session_events."""

# ruff: noqa: F403

from runefoble_events.events import session_events
from runefoble_events.events.session_events import *

__all__ = list(session_events.__all__)
