"""Process-wide speech synthesizer selected from configuration."""

from __future__ import annotations

from voice_agent.speech_settings import VoiceAgentSettings, build_synthesizer
from voice_agent.synthesizer import BaseSynthesizer

_synthesizer: BaseSynthesizer | None = None


def get_speech_synthesizer() -> BaseSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = build_synthesizer(VoiceAgentSettings())
    return _synthesizer


def set_speech_synthesizer(synthesizer: BaseSynthesizer | None) -> None:
    """Replace the synthesizer. Pass None to rebuild it from settings on next use."""
    global _synthesizer
    _synthesizer = synthesizer
