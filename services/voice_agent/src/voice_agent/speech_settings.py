"""Voice Agent speech settings and the engine composition steps."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from runefoble_platform.engine_ports import build_adapter
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
    stt_model_dir: str | None = None
    stt_download_enabled: bool = True

    tts_engine: Literal["espeak-ng"] = "espeak-ng"
    tts_binary: str = "espeak-ng"


def build_transcriber(settings: VoiceAgentSettings) -> BaseTranscriber:
    """Select the configured speech-to-text adapter."""
    return build_adapter(
        "RUNEFOBLE_VOICE_STT_ENGINE",
        settings.stt_engine,
        {
            "faster-whisper": lambda: FasterWhisperTranscriber(
                model_size=settings.stt_model_size,
                device=settings.stt_device,
                compute_type=settings.stt_compute_type,
                model_dir=settings.stt_model_dir,
                download_enabled=settings.stt_download_enabled,
            ),
        },
    )


def build_synthesizer(settings: VoiceAgentSettings) -> BaseSynthesizer:
    """Select the configured text-to-speech adapter."""
    return build_adapter(
        "RUNEFOBLE_VOICE_TTS_ENGINE",
        settings.tts_engine,
        {"espeak-ng": lambda: EspeakNgSynthesizer(binary=settings.tts_binary)},
    )
