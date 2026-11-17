"""Text-to-speech port and the audio clip it returns."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


class SpeechSynthesisUnavailable(RuntimeError):
    """The speech engine cannot render the text into audio."""


@dataclass(frozen=True)
class AudioClip:
    """Signed 16-bit little-endian mono PCM with its sample rate."""

    pcm: bytes
    sample_rate: int

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        if len(self.pcm) % 2 != 0:
            raise ValueError("pcm must hold whole 16-bit samples")

    @property
    def sample_count(self) -> int:
        return len(self.pcm) // 2

    @property
    def duration_ms(self) -> float:
        """Duration derived from the sample count and the sample rate."""
        return round(self.sample_count * 1000.0 / self.sample_rate, 3)


class BaseSynthesizer(ABC):
    """Port: renders text into an audio clip."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> AudioClip:
        """Render text with the named voice.

        Raises SpeechSynthesisUnavailable when the engine cannot produce audio.
        """

    @abstractmethod
    async def check_ready(self) -> None:
        """Verify that the engine can run now, without synthesizing text.

        Raises SpeechSynthesisUnavailable when the engine is missing or broken.
        """
