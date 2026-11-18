"""Voice Agent player speech transcription router.

Audio goes through the STT port. Typed text is labelled as client text. The route never
invents player words (TASK-0602).
"""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from runefoble_events.events import PlayerSpokeEvent
from voice_agent.auth import get_voice_principal
from voice_agent.dependencies import (
    STREAM_SESSION,
    WATCHER_URL,
    get_event_bus,
    to_uuid,
)
from voice_agent.models import TranscribeRequest, TranscribeResponse
from voice_agent.stt import get_streaming_pipeline, parse_audio_data

logger = logging.getLogger("runefoble.voice_agent.transcribe")
router = APIRouter(
    dependencies=[Depends(get_voice_principal)], tags=["Speech Synthesis & Transcription"]
)

TranscriptSource = Literal["audio", "client_text"]


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
        spoken = await get_streaming_pipeline().transcriber.transcribe(pcm, sample_rate=sample_rate)
        return spoken.strip(), "audio"

    typed = (req.transcript or "").strip()
    if typed:
        return typed, "client_text"
    raise HTTPException(
        status_code=422,
        detail="Send audio_base64 or a non-empty transcript.",
    )


@router.post("/api/v1/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_speech(req: TranscribeRequest):
    """Transcribe player speech, emit PlayerSpokeEvent, and forward to The Watcher.

    Audio goes through the STT port. Typed text is used as given. Audio that yields no words
    publishes nothing and forwards nothing.
    """
    transcript, source = await _transcript_from_request(req)
    if not transcript:
        return TranscribeResponse(
            transcript="",
            source=source,
            speaker_id=req.speaker_id,
            speaker_name=req.speaker_name,
        )
    session_uuid = to_uuid(req.session_id)
    campaign_uuid = to_uuid(req.campaign_id)

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
    bus = get_event_bus()
    event_entry_id = None
    try:
        event_entry_id = await bus.publish_event(STREAM_SESSION, spoke_event)
    except Exception as e:
        logger.warning(
            "Failed to publish PlayerSpokeEvent to Redis stream '%s': %s", STREAM_SESSION, e
        )

    # 2. Forward to The Watcher
    watcher_intent = None
    try:
        watcher_client = get_streaming_pipeline()._watcher_client
        if watcher_client:
            resp = await watcher_client.post(
                "/api/v1/watcher/transcribe-and-act",
                json={
                    "speaker_id": req.speaker_id,
                    "speaker_name": req.speaker_name,
                    "transcript": transcript,
                    "session_id": req.session_id,
                    "campaign_id": req.campaign_id,
                },
            )
            if resp.status_code == 200:
                watcher_intent = resp.json()
        else:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{WATCHER_URL}/api/v1/watcher/transcribe-and-act",
                    json={
                        "speaker_id": req.speaker_id,
                        "speaker_name": req.speaker_name,
                        "transcript": transcript,
                        "session_id": req.session_id,
                        "campaign_id": req.campaign_id,
                    },
                )
                if resp.status_code == 200:
                    watcher_intent = resp.json()
    except Exception as e:
        logger.warning("Failed to forward transcript to The Watcher: %s", e)

    return TranscribeResponse(
        transcript=transcript,
        source=source,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        event_id=event_entry_id,
        watcher_intent=watcher_intent,
    )
