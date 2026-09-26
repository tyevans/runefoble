"""Whisper and Acoustic Transcription Providers for Streaming Audio."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("runefoble.voice_agent.transcriber")


class BaseTranscriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe PCM audio bytes into text."""


class MockWhisperTranscriber(BaseTranscriber):
    """Deterministic mock Whisper transcriber for offline execution and CI tests."""

    def __init__(
        self,
        default_transcript: str = "I move 3 squares north",
        simulated_latency_ms: float = 5.0,
    ):
        self.default_transcript = default_transcript
        self.simulated_latency_ms = simulated_latency_ms
        self.canned_transcripts: list[str] = []
        self._transcription_history: list[bytes] = []

    def set_canned_transcript(self, transcript: str) -> None:
        self.canned_transcripts = [transcript]

    def queue_canned_transcript(self, transcript: str) -> None:
        self.canned_transcripts.append(transcript)

    def clear(self) -> None:
        self.canned_transcripts.clear()
        self._transcription_history.clear()

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        self._transcription_history.append(audio_bytes)
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)
        if self.canned_transcripts:
            return self.canned_transcripts.pop(0)
        return self.default_transcript


class FasterWhisperTranscriber(BaseTranscriber):
    """Whisper acoustic transcriber using faster-whisper CTranslate2 runtime."""

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
            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.model_size, device=self.device, compute_type=self.compute_type
                )
            except Exception as e:
                logger.warning(
                    "faster-whisper model '%s' unavailable (%s). Falling back to mock.",
                    self.model_size,
                    e,
                )
                self._model = False
        return self._model

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        model = self._get_model()
        if not model:
            return "I move 3 squares north"

        def _infer() -> str:
            import numpy as np

            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _info = model.transcribe(audio_array, language="en", beam_size=1)
            return " ".join(seg.text for seg in segments).strip()

        return await asyncio.to_thread(_infer)
