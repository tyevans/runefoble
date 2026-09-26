"""Domain events for live WebRTC voice room signaling and audio peer management."""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.voice.peer_joined")
class VoicePeerJoined(BaseRunefobleEvent):
    """Emitted when an audio peer connects and joins the session voice room."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.peer_joined"
    session_id: str
    peer_id: str
    user_id: str
    role: str = "player"
    joined_at: str


@register_event("runefoble.events.voice.peer_left")
class VoicePeerLeft(BaseRunefobleEvent):
    """Emitted when an audio peer leaves or is disconnected/kicked from the voice room."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.peer_left"
    session_id: str
    peer_id: str
    reason: str = "disconnected"


@register_event("runefoble.events.voice.mute_toggled")
class VoicePeerMuteToggled(BaseRunefobleEvent):
    """Emitted when an audio peer toggles their microphone mute state."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.mute_toggled"
    session_id: str
    peer_id: str
    is_muted: bool = False
