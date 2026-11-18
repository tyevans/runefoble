"""Domain events for duplex TTS playback state in a voice room (TASK-0577)."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.voice.playback_started")
class VoicePlaybackStarted(BaseRunefobleEvent):
    """Emitted when TTS narration playback starts in a voice room."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.playback_started"
    session_id: str
    playback_id: str
    original_text: str = ""
    duration_ms: float = 10000.0
    started_at: float


@register_event("runefoble.events.voice.playback_attenuated")
class VoicePlaybackAttenuated(BaseRunefobleEvent):
    """Emitted when player speech starts a soft fade of active TTS playback."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.playback_attenuated"
    session_id: str
    playback_id: str
    speaker_id: str
    speaker_name: str = "Player"
    cutoff_position_ms: float = 0.0
    remaining_narration_text: str = ""
    fade_ms: float = 20.0


@register_event("runefoble.events.voice.playback_stopped")
class VoicePlaybackStopped(BaseRunefobleEvent):
    """Emitted when TTS narration playback ends, by barge-in or by a stop command."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.playback_stopped"
    session_id: str
    playback_id: str
    reason: str = "player_barge_in"


__all__ = [
    "VoicePlaybackAttenuated",
    "VoicePlaybackStarted",
    "VoicePlaybackStopped",
]
