"""Audio crossfade and cancellation token coordination for voice duplex playback interruption (TASK-0141).

Halts active TTS narration within < 100ms with a 20ms soft crossfade to silence.
"""

from __future__ import annotations

import array
import contextlib
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from runefoble_events.events import VoiceSpeechInterrupted


def apply_soft_crossfade(
    audio_bytes: bytes, fade_duration_ms: float = 20.0, sample_rate: int = 16000
) -> bytes:
    """Apply smooth 20ms cosine crossfade to silence on 16-bit signed PCM audio."""
    if not audio_bytes:
        return b""
    samples = array.array("h", audio_bytes)
    fade_samples = min(len(samples), int(sample_rate * (fade_duration_ms / 1000.0)))
    if fade_samples <= 0:
        return bytes(samples)
    start_idx = max(0, len(samples) - fade_samples)
    for i in range(fade_samples):
        multiplier = 0.5 * (1.0 + math.cos(math.pi * i / fade_samples))
        samples[start_idx + i] = int(samples[start_idx + i] * multiplier)
    return bytes(samples)


@dataclass
class PlaybackCancellationToken:
    """Thread-safe cancellation token for active audio playback tasks."""

    is_canceled: bool = False
    _callbacks: list[Callable[[], None]] = field(default_factory=list)

    def cancel(self) -> None:
        self.is_canceled = True
        for cb in self._callbacks:
            with contextlib.suppress(Exception):
                cb()

    def add_callback(self, cb: Callable[[], None]) -> None:
        if self.is_canceled:
            cb()
        else:
            self._callbacks.append(cb)


@dataclass
class InterruptionResult:
    """Result of an interrupted TTS narration stream."""

    playback_id: str
    session_id: str
    interrupted_by_speaker_id: str
    interrupted_by_speaker_name: str
    cutoff_position_ms: float
    playback_duration_ms: float
    remaining_narration_text: str
    original_text: str
    timestamp: float
    faded_audio_bytes: bytes | None = None

    def to_event(self) -> VoiceSpeechInterrupted:
        iso_now = datetime.fromtimestamp(self.timestamp, tz=UTC).isoformat()
        return VoiceSpeechInterrupted(
            session_id=self.session_id,
            speaker_id=self.interrupted_by_speaker_id,
            speaker_name=self.interrupted_by_speaker_name,
            timestamp=self.timestamp,
            interrupted_at=iso_now,
            remaining_narration_text=self.remaining_narration_text,
            original_text=self.original_text,
            playback_duration_ms=self.playback_duration_ms,
            cutoff_position_ms=self.cutoff_position_ms,
            reason="player_barge_in",
        )


class ActivePlayback:
    """Represents ongoing TTS speech stream capable of immediate soft interruption."""

    def __init__(
        self,
        playback_id: str,
        session_id: str,
        original_text: str,
        total_duration_ms: float = 10000.0,
    ) -> None:
        self.playback_id = playback_id
        self.session_id = session_id
        self.original_text = original_text
        self.total_duration_ms = total_duration_ms
        self.start_time = time.time()
        self.token = PlaybackCancellationToken()

    def interrupt(
        self, speaker_id: str, speaker_name: str, audio_tail: bytes | None = None
    ) -> InterruptionResult:
        self.token.cancel()
        now = time.time()
        cutoff_pos = min(self.total_duration_ms, max(0.0, (now - self.start_time) * 1000.0))
        ratio = cutoff_pos / max(1.0, self.total_duration_ms)
        words = self.original_text.split()
        cutoff_idx = min(len(words), int(len(words) * ratio))
        rem_text = " ".join(words[cutoff_idx:]) if ratio < 1.0 and words else ""
        return InterruptionResult(
            playback_id=self.playback_id,
            session_id=self.session_id,
            interrupted_by_speaker_id=speaker_id,
            interrupted_by_speaker_name=speaker_name,
            cutoff_position_ms=round(cutoff_pos, 2),
            playback_duration_ms=round(self.total_duration_ms, 2),
            remaining_narration_text=rem_text,
            original_text=self.original_text,
            timestamp=now,
            faded_audio_bytes=apply_soft_crossfade(audio_tail) if audio_tail else None,
        )


__all__ = [
    "ActivePlayback",
    "InterruptionResult",
    "PlaybackCancellationToken",
    "apply_soft_crossfade",
]
