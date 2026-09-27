"""Unified Acoustic Echo Cancellation Pipeline (TASK-0169).

Coordinates NLMS adaptive filtering, Double-Talk Detection, and Residual Echo Suppression.
"""

from __future__ import annotations

import array
import math

from voice_agent.aec.double_talk import DoubleTalkDetector, DoubleTalkState, ResidualEchoSuppressor
from voice_agent.aec.nlms_filter import NLMSAECFilter


class AECPipeline:
    """Integrated AEC processor coordinating NLMS adaptive filter, DTD, and RES."""

    def __init__(
        self,
        sample_rate: int = 16000,
        filter_length: int = 512,
        step_size: float = 0.25,
        frame_size_ms: float = 10.0,
        suppression_db: float = 28.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_samples = max(16, int(sample_rate * (frame_size_ms / 1000.0)))
        self.filter = NLMSAECFilter(filter_length=filter_length, step_size=step_size)
        self.dtd = DoubleTalkDetector(sample_rate=sample_rate)
        self.res = ResidualEchoSuppressor(suppression_db=suppression_db)

    def reset(self) -> None:
        """Reset internal filter and detector states."""
        self.filter.reset()
        self.dtd.reset()

    def process_pcm(self, ref_pcm: bytes, mic_pcm: bytes) -> tuple[bytes, dict]:
        """Process microphone audio against reference loudspeaker audio."""
        if not mic_pcm:
            return b"", {"erle_db": 0.0, "double_talk_detected": False, "echo_detected": False}

        mic_arr = array.array("h", mic_pcm)
        ref_arr = array.array("h", ref_pcm) if ref_pcm else array.array("h", [0] * len(mic_arr))
        if len(ref_arr) < len(mic_arr):
            ref_arr.extend([0] * (len(mic_arr) - len(ref_arr)))

        out_samples = array.array("h")
        dt_occurred = False
        echo_occurred = False
        n_total = len(mic_arr)

        for offset in range(0, n_total, self.frame_samples):
            chunk_len = min(self.frame_samples, n_total - offset)
            ref_chunk = ref_arr[offset : offset + chunk_len]
            mic_chunk = mic_arr[offset : offset + chunk_len]

            state = self.dtd.detect(ref_chunk, mic_chunk)
            if state == DoubleTalkState.DOUBLE_TALK:
                dt_occurred = True
            elif state == DoubleTalkState.FAR_END_ONLY:
                echo_occurred = True

            err_chunk, _ = self.filter.process_block(
                ref_chunk, mic_chunk, adapt=self.dtd.should_adapt
            )
            clean_chunk = self.res.suppress(err_chunk, state)

            for s in clean_chunk:
                clamped = max(-32768, min(32767, int(math.copysign(math.floor(abs(s) + 0.5), s))))
                out_samples.append(clamped)

        in_energy = sum(float(x) * float(x) for x in mic_arr)
        out_energy = sum(float(x) * float(x) for x in out_samples)
        erle = 10.0 * math.log10(in_energy / (out_energy + 1e-6)) if in_energy > 0 else 0.0

        stats = {
            "erle_db": round(erle, 2),
            "double_talk_detected": dt_occurred,
            "echo_detected": echo_occurred,
            "in_energy": in_energy,
            "out_energy": out_energy,
        }
        return bytes(out_samples), stats

    def benchmark(
        self,
        ref_pcm: bytes,
        mic_pcm: bytes,
        target_erle_db: float = 35.0,
    ) -> dict:
        """Run benchmark validating ERLE and double-talk metrics."""
        self.reset()
        clean_pcm, stats = self.process_pcm(ref_pcm, mic_pcm)
        erle = stats["erle_db"]
        mic_samples = array.array("h", mic_pcm)
        n = len(mic_samples) or 1

        return {
            "erle_db": erle,
            "target_erle_db": target_erle_db,
            "passed": erle >= target_erle_db,
            "double_talk_detected": stats["double_talk_detected"],
            "echo_detected": stats["echo_detected"],
            "initial_rms": round(math.sqrt(stats["in_energy"] / n), 2),
            "residual_rms": round(math.sqrt(stats["out_energy"] / n), 2),
            "cleaned_pcm": clean_pcm,
        }


__all__ = ["AECPipeline"]
