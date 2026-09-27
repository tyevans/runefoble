"""CloudEvents definitions for acoustic echo cancellation and ERLE validation."""

from __future__ import annotations

import time
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("voice.echo_suppression_engaged")
@register_event("runefoble.events.voice.echo_suppression_engaged")
class EchoSuppressionEngagedEvent(BaseRunefobleEvent):
    """Emitted when acoustic echo suppression is engaged on microphone stream."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.echo_suppression_engaged"
    session_id: str
    speaker_id: str = "default"
    erle_db: float = 0.0
    attenuation_db: float = 0.0
    engaged_at: float = Field(default_factory=time.time)
    is_double_talk: bool = False


@register_event("voice.aec_benchmark_completed")
@register_event("runefoble.events.voice.aec_benchmark_completed")
class AECBenchmarkCompletedEvent(BaseRunefobleEvent):
    """Emitted when hardware AEC benchmark finishes validating ERLE > 35dB."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceRoom"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.aec_benchmark_completed"
    session_id: str
    erle_db: float
    target_erle_db: float = 35.0
    passed: bool = True
    double_talk_detected: bool = False
    filter_length: int = 512
    completed_at: float = Field(default_factory=time.time)


# Backward-compatible aliases
EchoSuppressionEngaged = EchoSuppressionEngagedEvent
AECBenchmarkCompleted = AECBenchmarkCompletedEvent

__all__ = [
    "AECBenchmarkCompleted",
    "AECBenchmarkCompletedEvent",
    "EchoSuppressionEngaged",
    "EchoSuppressionEngagedEvent",
]
