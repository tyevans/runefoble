"""Speech-to-text port and the production faster-whisper adapter."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

logger = logging.getLogger("runefoble.voice_agent.transcriber")


class SpeechEngineUnavailable(RuntimeError):
    """The speech engine cannot load its model or cannot infer a transcript."""


class BaseTranscriber(ABC):
    """Port: transcribes PCM audio bytes into text."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe PCM audio bytes into text.

        Raises SpeechEngineUnavailable when the engine cannot produce a transcript.
        """


class FasterWhisperTranscriber(BaseTranscriber):
    """Whisper acoustic transcriber using the faster-whisper CTranslate2 runtime."""

    engine_name: ClassVar[str] = "faster-whisper"

    def __init__(
        self,
        model_size: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self._model

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        def _infer() -> str:
            import numpy as np

            model = self._get_model()
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _info = model.transcribe(audio_array, language="en", beam_size=1)
            return " ".join(seg.text for seg in segments).strip()

        try:
            return await asyncio.to_thread(_infer)
        except Exception as e:
            logger.warning("faster-whisper model '%s' failed: %s", self.model_size, e)
            raise SpeechEngineUnavailable(
                f"faster-whisper model '{self.model_size}' failed: {e}"
            ) from e
