"""Parse one frame of the audio stream WebSocket (TASK-0915).

A binary frame is raw audio. A text frame is a JSON object. Its optional fields change the
session, speaker, or campaign for this frame and the frames after it. A text frame that cannot
be parsed raises `ValueError`. The route answers it with an `INVALID_FRAME` error frame.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, replace

from pydantic import BaseModel, ValidationError

DEFAULT_SAMPLE_RATE = 16000

FRAME_PARSE_ERRORS: tuple[type[Exception], ...] = (ValidationError, binascii.Error, ValueError)
"""The errors that `parse_text_frame` raises for a frame that cannot be parsed."""


@dataclass(frozen=True)
class StreamContext:
    """The session, speaker, and campaign that the next frame belongs to."""

    session_id: str
    speaker_id: str
    speaker_name: str
    campaign_id: str


@dataclass(frozen=True)
class AudioFrame:
    """One parsed frame: its audio and the stream context it applies to."""

    context: StreamContext
    audio_bytes: bytes = b""
    sample_rate: int = DEFAULT_SAMPLE_RATE
    is_final: bool = False


class _TextFrame(BaseModel):
    audio_data: str | None = None
    audio_base64: str | None = None
    session_id: str | None = None
    speaker_id: str | None = None
    speaker_name: str | None = None
    campaign_id: str | None = None
    is_final: bool = False
    sample_rate: int = DEFAULT_SAMPLE_RATE


def parse_text_frame(text: str, context: StreamContext) -> AudioFrame:
    """Parse one JSON text frame. Raise one of `FRAME_PARSE_ERRORS` when it is malformed."""
    frame = _TextFrame.model_validate_json(text)
    encoded = frame.audio_data or frame.audio_base64
    audio = base64.b64decode(encoded, validate=True) if encoded else b""
    next_context = replace(
        context,
        session_id=frame.session_id or context.session_id,
        speaker_id=frame.speaker_id or context.speaker_id,
        speaker_name=frame.speaker_name or context.speaker_name,
        campaign_id=frame.campaign_id or context.campaign_id,
    )
    return AudioFrame(
        context=next_context,
        audio_bytes=audio,
        sample_rate=frame.sample_rate,
        is_final=frame.is_final,
    )


__all__ = [
    "FRAME_PARSE_ERRORS",
    "AudioFrame",
    "StreamContext",
    "parse_text_frame",
]
