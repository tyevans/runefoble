"""Backwards-compatibility alias for runefoble_events.events.board_events."""

# ruff: noqa: F403

from runefoble_events.events import board_events
from runefoble_events.events.board_events import *

__all__ = list(board_events.__all__)
