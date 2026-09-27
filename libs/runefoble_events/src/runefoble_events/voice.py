"""Domain events for live WebRTC voice room signaling and audio peer management."""

import time
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


@register_event("runefoble.events.voice.mobile_connected")
class MobileCompanionConnected(BaseRunefobleEvent):
    """Emitted when a mobile companion connects via the low-bandwidth gateway."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.mobile_connected"
    session_id: str
    peer_id: str
    user_id: str
    device_type: str = "mobile"
    audio_profile_tier: str = "mobile_optimized"
    haptic_supported: bool = True
    connected_at: str


@register_event("runefoble.events.voice.profile_adapted")
class MobileAudioProfileAdapted(BaseRunefobleEvent):
    """Emitted when mobile companion audio adapts due to cellular network conditions."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.profile_adapted"
    session_id: str
    peer_id: str
    user_id: str
    previous_tier: str
    current_tier: str
    sample_rate: int = 16000
    bitrate_kbps: int = 16
    packet_loss: float = 0.0
    reason: str = "network_condition_changed"


@register_event("runefoble.events.voice.haptic_ping")
class MobileHapticPingDispatched(BaseRunefobleEvent):
    """Emitted when a haptic vibration pulse or lockscreen alert is dispatched to mobile."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.haptic_ping"
    session_id: str
    recipient_id: str
    alert_type: str = "secret_whisper"
    vibration_pattern: list[int] = Field(default_factory=lambda: [200, 100, 200])
    whisper_content: str | None = None
    notification_title: str | None = None
    notification_body: str | None = None
    diegetic: bool = True
    dispatched_at: str


@register_event("voice.speech.interrupted")
@register_event("runefoble.events.voice.speech_interrupted")
class VoiceSpeechInterrupted(BaseRunefobleEvent):
    """Emitted when active TTS playback/narration is interrupted by player speech (barge-in)."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "voice.speech.interrupted"
    session_id: str
    speaker_id: str
    speaker_name: str = "Player"
    timestamp: float = Field(default_factory=time.time)
    interrupted_at: str | None = None
    remaining_narration_text: str | None = None
    original_text: str | None = None
    playback_duration_ms: float = 0.0
    cutoff_position_ms: float = 0.0
    reason: str = "player_barge_in"
