"""Audio crossfade and cancellation token coordination for voice duplex playback interruption (TASK-0141).

Halts active TTS narration within < 100ms with a 20ms soft crossfade to silence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from runefoble_events.events import VoiceSpeechInterrupted
from voice_agent.dsp.cosine_crossfade import apply_cosine_crossfade
from voice_agent.room_aggregate import VoicePlaybackState


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


def build_interruption(
    playback: VoicePlaybackState,
    speaker_id: str,
    speaker_name: str,
    *,
    now: float,
    audio_tail: bytes | None = None,
) -> InterruptionResult:
    """Compute the cutoff and remaining narration for playback stopped at time `now` (TASK-0577).

    The playback state comes from the room aggregate. Nothing is cached in process.
    """
    total = playback.duration_ms
    cutoff_pos = min(total, max(0.0, (now - playback.started_at) * 1000.0))
    ratio = cutoff_pos / max(1.0, total)
    words = playback.original_text.split()
    cutoff_idx = min(len(words), int(len(words) * ratio))
    rem_text = " ".join(words[cutoff_idx:]) if ratio < 1.0 and words else ""
    return InterruptionResult(
        playback_id=playback.playback_id,
        session_id=playback.session_id,
        interrupted_by_speaker_id=speaker_id,
        interrupted_by_speaker_name=speaker_name,
        cutoff_position_ms=round(cutoff_pos, 2),
        playback_duration_ms=round(total, 2),
        remaining_narration_text=rem_text,
        original_text=playback.original_text,
        timestamp=now,
        faded_audio_bytes=apply_cosine_crossfade(audio_tail) if audio_tail else None,
    )


__all__ = [
    "InterruptionResult",
    "build_interruption",
]
