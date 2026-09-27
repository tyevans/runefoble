"""CloudEvents definitions for neural speech barge-in and TTS stream attenuation."""

from __future__ import annotations

import time
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("voice.barge_in_detected")
@register_event("runefoble.events.voice.barge_in_detected")
class NeuralSpeechBargeInDetectedEvent(BaseRunefobleEvent):
    """Emitted when neural VAD detects vocalization onset during active TTS playback."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.barge_in_detected"
    session_id: str
    speaker_id: str
    speaker_name: str = "Player"
    onset_latency_ms: float = 0.0
    confidence: float = 1.0
    rms_energy: float = 0.0
    detected_at: float = Field(default_factory=time.time)
    reason: str = "human_speech_barge_in"


@register_event("voice.tts_stream_attenuated")
@register_event("runefoble.events.voice.tts_stream_attenuated")
class TTSStreamAttenuatedEvent(BaseRunefobleEvent):
    """Emitted when active TTS playback is attenuated gracefully to silence with cosine crossfading."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.tts_stream_attenuated"
    session_id: str
    stream_id: str = "tts_stream"
    fade_duration_ms: float = 20.0
    attenuated_samples_count: int = 0
    peak_tail_amplitude: int = 0
    cutoff_position_ms: float = 0.0
    remaining_text: str | None = None
    attenuated_at: float = Field(default_factory=time.time)


# Backward-compatible aliases
NeuralSpeechBargeInDetected = NeuralSpeechBargeInDetectedEvent
TTSStreamAttenuated = TTSStreamAttenuatedEvent

__all__ = [
    "NeuralSpeechBargeInDetected",
    "NeuralSpeechBargeInDetectedEvent",
    "TTSStreamAttenuated",
    "TTSStreamAttenuatedEvent",
]
