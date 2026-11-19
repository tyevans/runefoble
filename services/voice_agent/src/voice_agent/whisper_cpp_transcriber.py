"""whisper.cpp HTTP speech-to-text adapter (TASK-0833).

The adapter posts each utterance as a WAV file to a whisper.cpp server at `{base_url}/inference`
and returns the transcript from the JSON reply. Any transport error, non-2xx status, or reply
without a transcript raises EngineUnavailableError. The adapter never returns substitute text.
"""

from __future__ import annotations

from typing import ClassVar

import httpx
from runefoble_platform.engine_ports import EngineUnavailableError
from voice_agent.synthesizer import AudioClip
from voice_agent.transcriber import SPEECH_ENGINE_UNAVAILABLE, BaseTranscriber
from voice_agent.wav import encode_wav

HEALTH_TIMEOUT_SECONDS = 5.0


class WhisperCppTranscriber(BaseTranscriber):
    """Transcribes utterances with a whisper.cpp server reached over HTTP."""

    engine_name: ClassVar[str] = "whisper-cpp"

    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _unavailable(self, reason: str) -> EngineUnavailableError:
        return EngineUnavailableError(
            SPEECH_ENGINE_UNAVAILABLE,
            self.engine_name,
            f"whisper.cpp server at '{self.base_url}' {reason}",
        )

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        wav = encode_wav(AudioClip(pcm=audio_bytes, sample_rate=sample_rate))
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout_seconds
            ) as client:
                response = await client.post(
                    "/inference",
                    files={"file": ("utterance.wav", wav, "audio/wav")},
                    data={"response_format": "json", "temperature": "0.0"},
                )
        except httpx.HTTPError as exc:
            raise self._unavailable(f"is unreachable: {exc}") from exc
        if not response.is_success:
            raise self._unavailable(f"answered HTTP {response.status_code} to inference")
        try:
            text = response.json()["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise self._unavailable("replied without a transcript") from exc
        if not isinstance(text, str):
            raise self._unavailable("replied with a transcript that is not text")
        return text.strip()

    async def check_ready(self) -> None:
        """The server must answer its health route. A stopped or failing server is not ready."""
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=HEALTH_TIMEOUT_SECONDS
            ) as client:
                response = await client.get("/health")
        except httpx.HTTPError as exc:
            raise self._unavailable(f"is unreachable: {exc}") from exc
        if not response.is_success:
            raise self._unavailable(f"answered HTTP {response.status_code} to health")
