"""Domain events for WebRTC voice stream network quality and adaptive bitrate changes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.voice.stream_quality_degraded")
class VoiceStreamQualityDegradedEvent(BaseRunefobleEvent):
    """Emitted when RTCP receiver reports detect packet loss or delay spikes exceeding limits."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.stream_quality_degraded"
    session_id: str
    peer_id: str
    user_id: str | None = None
    packet_loss: float = 0.0
    round_trip_time_ms: float = 0.0
    jitter_ms: float = 0.0
    severity: str = "degraded"
    detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


@register_event("runefoble.events.voice.stream_codec_adapted")
class VoiceStreamCodecAdaptedEvent(BaseRunefobleEvent):
    """Emitted when stream bitrate or Opus codec parameters are dynamically adjusted."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.stream_codec_adapted"
    session_id: str
    peer_id: str
    user_id: str | None = None
    previous_bitrate_kbps: int
    new_bitrate_kbps: int
    sample_rate: int = 16000
    channels: int = 1
    complexity: int = 5
    fec_enabled: bool = True
    dtx_enabled: bool = True
    codec_mode: str = "cellular_constrained"
    reason: str = "packet_loss_exceeded_threshold"
    adapted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


__all__ = [
    "VoiceStreamCodecAdaptedEvent",
    "VoiceStreamQualityDegradedEvent",
]
