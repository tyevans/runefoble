"""Speech engine readiness for the voice agent health route (ADR-0015).

A missing dependency fails the readiness check. It never degrades silently.
"""

from __future__ import annotations

from runefoble_platform.engine_ports import EngineUnavailableError
from voice_agent.synthesizer import BaseSynthesizer
from voice_agent.transcriber import BaseTranscriber


async def speech_readiness_problems(
    transcriber: BaseTranscriber, synthesizer: BaseSynthesizer
) -> dict[str, str]:
    """Return one message per speech engine that is not ready. An empty dict means ready."""
    problems: dict[str, str] = {}
    try:
        await transcriber.check_ready()
    except EngineUnavailableError as exc:
        problems["stt"] = str(exc)
    try:
        await synthesizer.check_ready()
    except EngineUnavailableError as exc:
        problems["tts"] = str(exc)
    return problems
