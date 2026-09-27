"""Normalized Least Mean Squares (NLMS) transversal adaptive filter for AEC (TASK-0169).

Computes loudspeaker acoustic transfer functions and cancels room echo signals.
"""

from __future__ import annotations

import array
import math
from collections import deque


class NLMSAECFilter:
    """Adaptive transversal filter computing loudspeaker room impulse responses."""

    def __init__(
        self,
        filter_length: int = 512,
        step_size: float = 0.25,
        leakage: float = 0.9999,
        eps: float = 1e-4,
    ) -> None:
        self.filter_length = filter_length
        self.step_size = step_size
        self.leakage = leakage
        self.eps = eps

        self.weights: list[float] = [0.0] * filter_length
        self.x_buf: deque[float] = deque([0.0] * filter_length, maxlen=filter_length)
        self._ref_power: float = 0.0

    def reset(self) -> None:
        """Reset adaptive weights and reference delay line."""
        self.weights = [0.0] * self.filter_length
        self.x_buf = deque([0.0] * self.filter_length, maxlen=self.filter_length)
        self._ref_power = 0.0

    def step(self, x: float, d: float, adapt: bool = True) -> tuple[float, float]:
        """Process a single sample pair (reference x, mic d).

        Returns:
            tuple[float, float]: (residual_error, estimated_echo)
        """
        old_x = self.x_buf[-1]
        self.x_buf.appendleft(x)
        self._ref_power += (x * x) - (old_x * old_x)
        if self._ref_power < 0.0:
            self._ref_power = 0.0

        # Estimate echo: y = w^T * x
        y = sum(w * xb for w, xb in zip(self.weights, self.x_buf, strict=False))
        err = d - y

        if adapt:
            norm = self.step_size / (self._ref_power + self.eps)
            factor = norm * err
            self.weights = [
                self.leakage * w + factor * xb
                for w, xb in zip(self.weights, self.x_buf, strict=False)
            ]

        return err, y

    def process_block(
        self,
        ref_samples: list[float] | array.array,
        mic_samples: list[float] | array.array,
        adapt: bool = True,
    ) -> tuple[list[float], list[float]]:
        """Process a block of reference and microphone samples."""
        n = min(len(ref_samples), len(mic_samples))
        errors: list[float] = [0.0] * n
        estimates: list[float] = [0.0] * n

        for i in range(n):
            e, y = self.step(float(ref_samples[i]), float(mic_samples[i]), adapt=adapt)
            errors[i] = e
            estimates[i] = y

        return errors, estimates

    def filter_pcm(
        self,
        ref_pcm: bytes,
        mic_pcm: bytes,
        adapt: bool = True,
    ) -> tuple[bytes, list[float], list[float]]:
        """Filter microphone PCM stream given reference loudspeaker PCM."""
        if not mic_pcm:
            return b"", [], []
        ref_arr = (
            array.array("h", ref_pcm) if ref_pcm else array.array("h", [0] * (len(mic_pcm) // 2))
        )
        mic_arr = array.array("h", mic_pcm)

        errors, estimates = self.process_block(ref_arr, mic_arr, adapt=adapt)
        out_samples = array.array("h")
        for err in errors:
            clamped = max(-32768, min(32767, int(math.copysign(math.floor(abs(err) + 0.5), err))))
            out_samples.append(clamped)

        return bytes(out_samples), errors, estimates


__all__ = ["NLMSAECFilter"]
