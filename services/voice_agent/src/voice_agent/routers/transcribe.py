"""Voice Agent player speech transcription router.

Audio goes through the STT port. Typed text is labelled as client text. The route never
invents player words (TASK-0602).
"""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import opaque_aggregate_id
from voice_agent.auth import CallerPrincipal, get_principal
from voice_agent.authz import require_speaker
from voice_agent.dependencies import STREAM_SESSION, get_event_bus
from voice_agent.models import TranscribeRequest, TranscribeResponse
from voice_agent.stt import get_streaming_pipeline, parse_audio_data

logger = logging.getLogger("runefoble.voice_agent.transcribe")
router = APIRouter(dependencies=[Depends(get_principal)], tags=["Speech Synthesis & Transcription"])

TranscriptSource = Literal["audio", "client_text"]
_BOARD_ORIGIN_FIELDS = {"token_id", "from_x", "from_y", "grid_cols", "grid_rows"}


async def _transcript_from_request(req: TranscribeRequest) -> tuple[str, TranscriptSource]:
    """Return the player's words and where they came from. Never invents text.

    Audio wins when both audio and typed text are sent. Malformed or empty input returns 422.
    Engine failures propagate as EngineUnavailableError, which the app maps to 503.
    """
    if req.audio_base64 is not None:
        try:
            audio = base64.b64decode(req.audio_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=422, detail="audio_base64 is not valid base64") from exc
        pcm, sample_rate = parse_audio_data(audio)
        if not pcm:
            raise HTTPException(status_code=422, detail="audio_base64 holds no audio")
        pipeline = get_streaming_pipeline()
        spoken = await pipeline.transcriber.transcribe(pcm, sample_rate=sample_rate)
        return spoken.strip(), "audio"

    typed = (req.transcript or "").strip()
    if typed:
        return typed, "client_text"
    raise HTTPException(
        status_code=422,
        detail="Send audio_base64 or a non-empty transcript.",
    )


@router.post("/api/v1/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_speech(
    req: TranscribeRequest,
    principal: CallerPrincipal,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """Transcribe player speech, emit PlayerSpokeEvent, and forward to The Watcher.

    Audio goes through the STT port. Typed text is used as given. Audio that yields no words
    publishes nothing and forwards nothing.
    """
    await require_speaker(req.session_id, req.speaker_id, principal.user_id)
    transcript, source = await _transcript_from_request(req)
    if not transcript:
        return TranscribeResponse(
            transcript="",
            source=source,
            speaker_id=req.speaker_id,
            speaker_name=req.speaker_name,
        )
    session_uuid = opaque_aggregate_id(req.session_id, field="session_id")
    campaign_uuid = opaque_aggregate_id(req.campaign_id, field="campaign_id")

    # 1. Emit PlayerSpokeEvent
    spoke_event = PlayerSpokeEvent(
        aggregate_id=session_uuid,
        session_id=session_uuid,
        campaign_id=campaign_uuid,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        transcript=transcript,
        is_whisper=req.is_whisper,
        target_character_id=req.target_character_id,
    )
    # The spoken words are player state. A failed publish returns 503 and forwards nothing.
    event_entry_id = await publish_or_fail(get_event_bus(), STREAM_SESSION, spoke_event)

    # 2. Forward to The Watcher with the speaker's own bearer (ADR-0015 c). A failed forward
    # keeps the transcript and reports the reason in `watcher_error` (TASK-0732).
    # The board origin goes with the transcript, so The Watcher can stage a move (TASK-0942).
    forwarded = await get_streaming_pipeline().watcher.forward(
        {
            "speaker_id": req.speaker_id,
            "speaker_name": req.speaker_name,
            "transcript": transcript,
            "session_id": req.session_id,
            "campaign_id": req.campaign_id,
            **req.model_dump(include=_BOARD_ORIGIN_FIELDS, exclude_none=True),
        },
        authorization,
    )
    if forwarded.error is not None:
        logger.warning("The Watcher did not take the transcript: %s", forwarded.error)

    return TranscribeResponse(
        transcript=transcript,
        source=source,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        event_id=event_entry_id,
        watcher_intent=forwarded.intent,
        watcher_error=forwarded.error,
    )
