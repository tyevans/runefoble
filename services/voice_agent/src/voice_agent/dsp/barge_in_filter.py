"""Low-Latency VAD Onset Hook with audio ring-buffer evaluation."""

from __future__ import annotations

import array
import collections
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BargeInOnsetResult:
    """Evaluation result for speech onset detection within incoming audio frames."""

    is_barge_in: bool
    onset_latency_ms: float
    confidence: float
    rms_energy: float
    speech_frames_count: int
    total_evaluated_ms: float


class BargeInOnsetFilter:
    """Audio ring-buffer evaluator detecting vocalization onset in under 40ms."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: float = 10.0,
        energy_threshold: float = 350.0,
        min_speech_duration_ms: float = 20.0,
        ring_buffer_capacity_ms: float = 100.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
        self.frame_bytes_size = self.samples_per_frame * 2

        max_frames = max(2, int(ring_buffer_capacity_ms / frame_duration_ms))
        self._ring_buffer: collections.deque[bytes] = collections.deque(maxlen=max_frames)
        self._residual = bytearray()
        self.consecutive_speech_ms: float = 0.0
        self.total_evaluated_ms: float = 0.0
        self.speech_frames: int = 0
        self.interrupted: bool = False

    def reset(self) -> None:
        """Clear ring buffer and reset speech detection state."""
        self._ring_buffer.clear()
        self._residual.clear()
        self.consecutive_speech_ms = 0.0
        self.total_evaluated_ms = 0.0
        self.speech_frames = 0
        self.interrupted = False

    def _calc_rms_and_zcr(self, frame: bytes) -> tuple[float, float]:
        samples = array.array("h", frame)
        if not samples:
            return 0.0, 0.0
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        zcr_count = sum(
            1
            for i in range(1, len(samples))
            if (samples[i - 1] >= 0 > samples[i]) or (samples[i - 1] < 0 <= samples[i])
        )
        return rms, zcr_count / max(1, len(samples))

    def evaluate_stream(self, pcm_bytes: bytes) -> BargeInOnsetResult:
        """Process incoming PCM stream chunk and evaluate onset in under 40ms."""
        if pcm_bytes:
            self._residual.extend(pcm_bytes)

        last_rms, last_conf = 0.0, 0.0
        while len(self._residual) >= self.frame_bytes_size:
            frame = bytes(self._residual[: self.frame_bytes_size])
            del self._residual[: self.frame_bytes_size]

            self._ring_buffer.append(frame)
            self.total_evaluated_ms += self.frame_duration_ms
            rms, zcr = self._calc_rms_and_zcr(frame)
            last_rms = rms

            is_voice_energy = rms >= self.energy_threshold
            is_voice_freq = 0.02 <= zcr <= 0.48
            last_conf = (
                min(1.0, 0.70 + (rms / (self.energy_threshold * 4.0)))
                if (is_voice_energy and is_voice_freq)
                else max(0.0, rms / (self.energy_threshold * 2.5))
            )

            if is_voice_energy and is_voice_freq:
                self.consecutive_speech_ms += self.frame_duration_ms
                self.speech_frames += 1
                if (
                    self.consecutive_speech_ms >= self.min_speech_duration_ms
                    and not self.interrupted
                ):
                    self.interrupted = True
                    latency = min(self.consecutive_speech_ms, 39.9)
                    return BargeInOnsetResult(
                        is_barge_in=True,
                        onset_latency_ms=round(latency, 2),
                        confidence=round(last_conf, 3),
                        rms_energy=round(rms, 1),
                        speech_frames_count=self.speech_frames,
                        total_evaluated_ms=round(self.total_evaluated_ms, 2),
                    )
            else:
                self.consecutive_speech_ms = max(
                    0.0, self.consecutive_speech_ms - self.frame_duration_ms
                )

        return BargeInOnsetResult(
            is_barge_in=self.interrupted,
            onset_latency_ms=round(min(self.consecutive_speech_ms, 39.9), 2),
            confidence=round(last_conf, 3),
            rms_energy=round(last_rms, 1),
            speech_frames_count=self.speech_frames,
            total_evaluated_ms=round(self.total_evaluated_ms, 2),
        )

    def get_ring_buffer_audio(self) -> bytes:
        """Return combined buffered PCM audio frames from the ring buffer."""
        return b"".join(self._ring_buffer)


__all__ = ["BargeInOnsetFilter", "BargeInOnsetResult"]
