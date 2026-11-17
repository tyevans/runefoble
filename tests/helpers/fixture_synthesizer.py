"""Deterministic speech synthesizer for the test composition root only.

The fixture renders each character as a fixed-length tone. The audio length
therefore grows with the text, and the same text always yields the same PCM.
Production code has no tone generator.
"""

from __future__ import annotations

import array
import math

from voice_agent.synthesizer import AudioClip, BaseSynthesizer

FIXTURE_SAMPLE_RATE = 16000
SAMPLES_PER_CHARACTER = 640  # 40 ms at 16 kHz


class FixtureSynthesizer(BaseSynthesizer):
    """Renders 40 ms of tone per character. Frequency depends on the character."""

    engine_name = "fixture"

    async def check_ready(self) -> None:
        return None

    async def synthesize(self, text: str, voice: str) -> AudioClip:
        samples = array.array("h")
        for char in text:
            step = 2.0 * math.pi * (200.0 + (ord(char) % 64) * 15.0) / FIXTURE_SAMPLE_RATE
            for i in range(SAMPLES_PER_CHARACTER):
                samples.append(int(8000 * math.sin(i * step)))
        return AudioClip(pcm=samples.tobytes(), sample_rate=FIXTURE_SAMPLE_RATE)
