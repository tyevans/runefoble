"""GameSession aggregate and spectator stream events."""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class SessionCreated(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    title: str = "Untitled Session"
    dm_id: str = "the_watcher"
    created_by: str = "system"


@register_event
class SessionStarted(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    started_at_turn: int = 1


@register_event
class PlayerJoinedSession(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str


@register_event
class PlayerLeftSession(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    player_id: str
    reason: str = "disconnected"


@register_event
class TurnAdvanced(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    previous_turn: int
    new_turn: int
    active_character_id: UUID | None = None


@register_event
class SessionEnded(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    summary: str = "Session completed"


@register_event("runefoble.events.spectator.connected")
class SpectatorSessionConnected(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Spectator"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.spectator.connected"
    session_id: str
    viewer_id: str
    viewer_name: str
    connected_at: str
