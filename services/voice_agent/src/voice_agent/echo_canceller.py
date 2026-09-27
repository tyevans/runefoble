"""Adaptive Acoustic Echo Cancellation (AEC) filter for voice duplex barge-in (TASK-0141).

Suppresses speaker output from microphone capture buffers, preventing false-positive barge-in triggers.
"""

from __future__ import annotations

import array
import math
from collections import deque


class AcousticEchoCanceller:
    """Adaptive echo filter subtracting speaker playback reference from microphone frames."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: float = 20.0,
        filter_length_samples: int = 320,  # 20ms at 16kHz
        learning_rate: float = 0.25,
        leakage: float = 0.999,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.filter_length = filter_length_samples
        self.learning_rate = learning_rate
        self.leakage = leakage

        # Adaptive filter weights initialized to zero
        self.weights = [0.0] * self.filter_length
        # Reference speaker history buffer (up to ~1s)
        self.ref_buffer: deque[int] = deque(maxlen=sample_rate)

    def reset(self) -> None:
        """Reset adaptive weights and reference speaker audio history."""
        self.weights = [0.0] * self.filter_length
        self.ref_buffer.clear()

    def register_speaker_output(self, speaker_pcm: bytes) -> None:
        """Buffer downstream speaker TTS playback for reference cancellation."""
        if not speaker_pcm:
            return
        samples = array.array("h", speaker_pcm)
        self.ref_buffer.extend(samples)

    def is_echo_dominant(self, mic_pcm: bytes, correlation_threshold: float = 0.55) -> bool:
        """Check whether incoming microphone frame is dominated by speaker acoustic echo."""
        if not mic_pcm or len(self.ref_buffer) < self.filter_length:
            return False
        mic_samples = array.array("h", mic_pcm)
        n = min(len(mic_samples), self.filter_length)
        ref_slice = list(self.ref_buffer)[-n:]

        dot_prod = sum(m * r for m, r in zip(mic_samples[:n], ref_slice, strict=False))
        mic_energy = sum(m * m for m in mic_samples[:n])
        ref_energy = sum(r * r for r in ref_slice)
        if mic_energy == 0 or ref_energy == 0:
            return False

        norm_corr = dot_prod / math.sqrt(mic_energy * ref_energy)
        return norm_corr >= correlation_threshold

    def filter_echo(self, mic_pcm: bytes) -> bytes:
        """Subtract estimated acoustic echo from microphone PCM buffer via Normalized LMS."""
        if not mic_pcm:
            return b""
        if len(self.ref_buffer) < self.filter_length:
            return mic_pcm

        mic_samples = array.array("h", mic_pcm)
        clean_samples = array.array("h", [0] * len(mic_samples))
        ref_list = list(self.ref_buffer)

        for i in range(len(mic_samples)):
            idx = len(ref_list) - len(mic_samples) + i
            if idx < self.filter_length:
                clean_samples[i] = mic_samples[i]
                continue

            ref_window = ref_list[idx - self.filter_length : idx]
            ref_energy = sum(x * x for x in ref_window) + 1e-6

            # Compute estimated echo: y_hat = w^T * x
            echo_est = sum(w * x for w, x in zip(self.weights, ref_window, strict=False))
            err = float(mic_samples[i]) - echo_est

            # NLMS weight adaptation with leakage: w = leakage * w + mu * err * x / (|x|^2 + eps)
            norm_factor = self.learning_rate / ref_energy
            for k in range(self.filter_length):
                self.weights[k] = self.leakage * self.weights[k] + norm_factor * err * ref_window[k]

            # Output error signal (clean speech estimate) clamped to int16 range
            clamped = max(-32768, min(32767, int(err)))
            clean_samples[i] = clamped

        return bytes(clean_samples)


__all__ = ["AcousticEchoCanceller"]
