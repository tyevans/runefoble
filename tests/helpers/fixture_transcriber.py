"""Deterministic speech engine for the test composition root only.

Production code has no canned transcript. Test fixtures inject this engine
into the streaming pipeline. Tests queue the transcript for each completed
utterance with `script`. Unqueued utterances return FIXTURE_TRANSCRIPT.
"""

from __future__ import annotations

from collections import deque

from voice_agent.transcriber import BaseTranscriber

FIXTURE_TRANSCRIPT = "fixture speech transcript"


class FixtureTranscriber(BaseTranscriber):
    """Returns queued transcripts in order, then FIXTURE_TRANSCRIPT."""

    engine_name = "fixture"

    def __init__(self) -> None:
        self._script: deque[str] = deque()

    def script(self, *transcripts: str) -> None:
        """Queue transcripts for the next completed utterances, in order."""
        self._script.extend(transcripts)

    async def check_ready(self) -> None:
        return None

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        if self._script:
            return self._script.popleft()
        return FIXTURE_TRANSCRIPT
