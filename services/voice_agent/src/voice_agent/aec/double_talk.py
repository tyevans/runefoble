"""Double-Talk Detector and Residual Echo Suppressor (TASK-0169).

Provides a finite state machine preventing NLMS divergence during simultaneous speech.
"""

from __future__ import annotations

import array
import math
from enum import StrEnum


class DoubleTalkState(StrEnum):
    """AEC conversation state modes."""

    SILENCE = "silence"
    FAR_END_ONLY = "far_end_only"
    NEAR_END_ONLY = "near_end_only"
    DOUBLE_TALK = "double_talk"


class DoubleTalkDetector:
    """State machine detecting double-talk to freeze adaptive weight updates."""

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 120.0,
        geigel_ratio: float = 0.75,
        hangover_frames: int = 6,
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.geigel_ratio = geigel_ratio
        self.hangover_frames = hangover_frames
        self.state: DoubleTalkState = DoubleTalkState.SILENCE
        self._hangover_count: int = 0

    def reset(self) -> None:
        """Reset state machine and hangover counters."""
        self.state = DoubleTalkState.SILENCE
        self._hangover_count = 0

    @property
    def should_adapt(self) -> bool:
        """Return True only when far-end echo is dominant without double-talk."""
        return self.state == DoubleTalkState.FAR_END_ONLY

    def detect(
        self,
        ref_block: list[float] | array.array,
        mic_block: list[float] | array.array,
        err_block: list[float] | None = None,
        echo_block: list[float] | None = None,
    ) -> DoubleTalkState:
        """Evaluate block energies and Geigel ratio to determine conversation state."""
        n = min(len(ref_block), len(mic_block))
        if n == 0:
            return self.state

        ref_energy = sum(float(x) * float(x) for x in ref_block[:n])
        mic_energy = sum(float(d) * float(d) for d in mic_block[:n])
        rms_ref = math.sqrt(ref_energy / n)
        rms_mic = math.sqrt(mic_energy / n)

        if rms_ref < self.energy_threshold and rms_mic < self.energy_threshold:
            self.state = DoubleTalkState.SILENCE
            return self.state

        if rms_ref < self.energy_threshold and rms_mic >= self.energy_threshold:
            self.state = DoubleTalkState.NEAR_END_ONLY
            return self.state

        # Far-end active: check for near-end speech using Geigel ratio
        is_dt = rms_mic > (self.geigel_ratio * rms_ref)

        if is_dt:
            self._hangover_count = self.hangover_frames
            self.state = DoubleTalkState.DOUBLE_TALK
        elif self._hangover_count > 0:
            self._hangover_count -= 1
            self.state = DoubleTalkState.DOUBLE_TALK
        else:
            self.state = DoubleTalkState.FAR_END_ONLY

        return self.state


class ResidualEchoSuppressor:
    """Post-filter attenuating residual echo leak during far-end speech."""

    def __init__(self, suppression_db: float = 28.0, min_gain: float = 0.01) -> None:
        self.suppression_db = suppression_db
        self.min_gain = min_gain
        self.gain = max(min_gain, 10.0 ** (-suppression_db / 20.0))

    def suppress(self, err_block: list[float], state: DoubleTalkState) -> list[float]:
        """Apply residual suppression only during far-end echo without human speech."""
        if state == DoubleTalkState.FAR_END_ONLY:
            return [s * self.gain for s in err_block]
        return err_block


__all__ = ["DoubleTalkDetector", "DoubleTalkState", "ResidualEchoSuppressor"]
