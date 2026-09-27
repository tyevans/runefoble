"""Event models aggregator facade for Runefoble reactive gameplay."""

# ruff: noqa: F403

from runefoble_events.events import (
    board_events,
    character_events,
    media_events,
    narrative_events,
    platform_events,
    session_events,
    world_events,
)
from runefoble_events.events.board_events import *
from runefoble_events.events.character_events import *
from runefoble_events.events.media_events import *
from runefoble_events.events.narrative_events import *
from runefoble_events.events.platform_events import *
from runefoble_events.events.session_events import *
from runefoble_events.events.world_events import *

__all__ = (
    board_events.__all__
    + character_events.__all__
    + media_events.__all__
    + narrative_events.__all__
    + platform_events.__all__
    + session_events.__all__
    + world_events.__all__
)
