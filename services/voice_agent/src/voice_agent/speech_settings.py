"""Voice Agent speech settings and the engine composition steps."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from voice_agent.espeak_synthesizer import EspeakNgSynthesizer
from voice_agent.synthesizer import BaseSynthesizer
from voice_agent.transcriber import BaseTranscriber, FasterWhisperTranscriber


class VoiceAgentSettings(BaseSettings):
    """Environment configuration for the voice agent (prefix RUNEFOBLE_VOICE_)."""

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_VOICE_",
        env_file=".env",
        extra="ignore",
    )

    stt_engine: Literal["faster-whisper"] = "faster-whisper"
    stt_model_size: str = "tiny.en"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"

    tts_engine: Literal["espeak-ng"] = "espeak-ng"
    tts_binary: str = "espeak-ng"


def build_transcriber(settings: VoiceAgentSettings) -> BaseTranscriber:
    """Select the configured speech engine adapter."""
    match settings.stt_engine:
        case "faster-whisper":
            return FasterWhisperTranscriber(
                model_size=settings.stt_model_size,
                device=settings.stt_device,
                compute_type=settings.stt_compute_type,
            )
    raise ValueError(f"Unsupported speech engine: {settings.stt_engine}")


def build_synthesizer(settings: VoiceAgentSettings) -> BaseSynthesizer:
    """Select the configured text-to-speech adapter."""
    match settings.tts_engine:
        case "espeak-ng":
            return EspeakNgSynthesizer(binary=settings.tts_binary)
    raise ValueError(f"Unsupported speech synthesis engine: {settings.tts_engine}")
