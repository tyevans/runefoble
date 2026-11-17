"""Speech-to-text port and the production faster-whisper adapter."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from runefoble_platform.engine_ports import EngineUnavailableError

logger = logging.getLogger("runefoble.voice_agent.transcriber")


def _hub_repo_dir(model_size: str) -> str:
    """Directory name that the Hugging Face cache uses for a faster-whisper model."""
    return f"models--Systran--faster-whisper-{model_size}"


SPEECH_ENGINE_UNAVAILABLE = "speech_engine_unavailable"


class BaseTranscriber(ABC):
    """Port: transcribes PCM audio bytes into text."""

    engine_name: ClassVar[str]

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe PCM audio bytes into text.

        Raises EngineUnavailableError when the engine cannot produce a transcript.
        """

    @abstractmethod
    async def check_ready(self) -> None:
        """Verify that the engine can transcribe without a network download.

        Raises EngineUnavailableError when the model is not available.
        """


class FasterWhisperTranscriber(BaseTranscriber):
    """Whisper acoustic transcriber using the faster-whisper CTranslate2 runtime."""

    engine_name: ClassVar[str] = "faster-whisper"

    def __init__(
        self,
        model_size: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8",
        model_dir: str | None = None,
        download_enabled: bool = True,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model_dir = model_dir
        self.download_enabled = download_enabled
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.model_dir,
                local_files_only=not self.download_enabled,
            )
        return self._model

    async def check_ready(self) -> None:
        """With download disabled, the model must already sit in the cache directory."""
        if self.download_enabled:
            return  # the model downloads on first use
        if not self.model_dir:
            raise EngineUnavailableError(
                SPEECH_ENGINE_UNAVAILABLE,
                self.engine_name,
                f"faster-whisper model '{self.model_size}' has no cache directory and "
                "download is disabled",
            )
        snapshots = Path(self.model_dir) / _hub_repo_dir(self.model_size) / "snapshots"
        if not snapshots.is_dir() or not any(snapshots.iterdir()):
            raise EngineUnavailableError(
                SPEECH_ENGINE_UNAVAILABLE,
                self.engine_name,
                f"faster-whisper model '{self.model_size}' is not cached in '{self.model_dir}' "
                "and download is disabled",
            )

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
            raise EngineUnavailableError(
                SPEECH_ENGINE_UNAVAILABLE,
                self.engine_name,
                f"faster-whisper model '{self.model_size}' failed: {e}",
            ) from e
