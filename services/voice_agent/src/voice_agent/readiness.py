"""Speech engine readiness for the voice agent health route (ADR-0015).

A missing dependency fails the readiness check. It never degrades silently.
"""

from __future__ import annotations

from voice_agent.synthesizer import BaseSynthesizer, SpeechSynthesisUnavailable
from voice_agent.transcriber import BaseTranscriber, SpeechEngineUnavailable


async def speech_readiness_problems(
    transcriber: BaseTranscriber, synthesizer: BaseSynthesizer
) -> dict[str, str]:
    """Return one message per speech engine that is not ready. An empty dict means ready."""
    problems: dict[str, str] = {}
    try:
        await transcriber.check_ready()
    except SpeechEngineUnavailable as exc:
        problems["stt"] = str(exc)
    try:
        await synthesizer.check_ready()
    except SpeechSynthesisUnavailable as exc:
        problems["tts"] = str(exc)
    return problems
