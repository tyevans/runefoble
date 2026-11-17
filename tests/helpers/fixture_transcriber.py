"""Deterministic speech engine for the test composition root only.

Production code has no canned transcript. Test fixtures inject this engine
into the streaming pipeline so that utterances without `mock_transcript`
produce a known, test-owned transcript.
"""

from __future__ import annotations

from voice_agent.transcriber import BaseTranscriber

FIXTURE_TRANSCRIPT = "fixture speech transcript"


class FixtureTranscriber(BaseTranscriber):
    """Returns FIXTURE_TRANSCRIPT for every completed utterance."""

    engine_name = "fixture"

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        return FIXTURE_TRANSCRIPT
