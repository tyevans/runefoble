"""Smooth Cosine Crossfade Attenuator for outgoing TTS audio streams."""

from __future__ import annotations

import array
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CosineAttenuationResult:
    """Result of cosine crossfade attenuation on outgoing audio samples."""

    faded_audio: bytes
    attenuated_samples_count: int
    peak_tail_amplitude: int
    max_discontinuity: int
    fade_duration_ms: float


def apply_cosine_crossfade(
    audio_bytes: bytes,
    fade_duration_ms: float = 20.0,
    sample_rate: int = 16000,
) -> bytes:
    """Apply smooth raised-cosine fade-out to silence on 16-bit signed PCM audio."""
    if not audio_bytes:
        return b""
    samples = array.array("h", audio_bytes)
    fade_samples = min(len(samples), int(sample_rate * (fade_duration_ms / 1000.0)))
    if fade_samples <= 0:
        return bytes(samples)

    start_idx = max(0, len(samples) - fade_samples)
    for i in range(fade_samples):
        # Raised-cosine smoothly falls to 0.0 at i = fade_samples - 1
        multiplier = 0.5 * (1.0 + math.cos(math.pi * (i + 1) / fade_samples))
        samples[start_idx + i] = int(samples[start_idx + i] * multiplier)
    return bytes(samples)


class CosineCrossfadeAttenuator:
    """Smooth 20ms cosine crossfade attenuator damping outgoing TTS samples to silence."""

    def __init__(self, fade_duration_ms: float = 20.0, sample_rate: int = 16000) -> None:
        self.fade_duration_ms = fade_duration_ms
        self.sample_rate = sample_rate

    def attenuate(
        self, audio_bytes: bytes, fade_duration_ms: float | None = None
    ) -> CosineAttenuationResult:
        """Damp the tail of outgoing audio samples to zero amplitude."""
        duration_ms = fade_duration_ms if fade_duration_ms is not None else self.fade_duration_ms
        if not audio_bytes:
            return CosineAttenuationResult(
                faded_audio=b"",
                attenuated_samples_count=0,
                peak_tail_amplitude=0,
                max_discontinuity=0,
                fade_duration_ms=duration_ms,
            )

        orig_samples = array.array("h", audio_bytes)
        faded_bytes = apply_cosine_crossfade(audio_bytes, duration_ms, self.sample_rate)
        faded_samples = array.array("h", faded_bytes)

        fade_count = min(len(orig_samples), int(self.sample_rate * (duration_ms / 1000.0)))
        peak_tail = abs(faded_samples[-1]) if faded_samples else 0

        # Calculate max delta between consecutive faded samples to assert no discontinuity pop
        max_delta = 0
        if len(faded_samples) > 1:
            start_check = max(0, len(faded_samples) - fade_count)
            max_delta = max(
                abs(faded_samples[i] - faded_samples[i - 1])
                for i in range(start_check + 1, len(faded_samples))
            )

        return CosineAttenuationResult(
            faded_audio=faded_bytes,
            attenuated_samples_count=fade_count,
            peak_tail_amplitude=peak_tail,
            max_discontinuity=max_delta,
            fade_duration_ms=duration_ms,
        )


__all__ = [
    "CosineAttenuationResult",
    "CosineCrossfadeAttenuator",
    "apply_cosine_crossfade",
]
