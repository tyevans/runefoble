"""HTTP and WebSocket routes for live audio streaming, VAD, and Whisper transcription."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from voice_agent.stt import get_streaming_pipeline

logger = logging.getLogger("runefoble.voice_agent.stream_routes")

router = APIRouter(prefix="/api/v1/voice/stream", tags=["Voice Stream STT"])


class AudioStreamChunkRequest(BaseModel):
    session_id: str
    speaker_id: str
    speaker_name: str
    campaign_id: str | None = None
    audio_data: str | None = None
    audio_base64: str | None = None
    sample_rate: int = 16000
    channels: int = 1
    is_whisper: bool = False
    target_character_id: str | None = None
    is_final: bool = False
    mock_transcript: str | None = None


class AudioStreamChunkResponse(BaseModel):
    session_id: str
    speaker_id: str
    speaker_name: str
    speech_detected: bool
    utterance_complete: bool
    transcript: str | None = None
    latency_ms: float = 0.0
    event_id: str | None = None
    watcher_intent: dict[str, Any] | None = None
    vad_state: str = "silence"
    buffer_duration_ms: float = 0.0


@router.post("/chunk", response_model=AudioStreamChunkResponse)
async def ingest_audio_chunk(req: AudioStreamChunkRequest):
    """Ingest PCM/WAV audio chunk, process VAD boundaries, and trigger streaming transcription."""
    raw_b64 = req.audio_data or req.audio_base64
    audio_bytes = b""
    if raw_b64:
        try:
            audio_bytes = base64.b64decode(raw_b64)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 audio payload: {e}",
            ) from e

    pipeline = get_streaming_pipeline()
    result = await pipeline.process_chunk(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        campaign_id=req.campaign_id,
        audio_bytes=audio_bytes,
        sample_rate=req.sample_rate,
        is_whisper=req.is_whisper,
        target_character_id=req.target_character_id,
        is_final=req.is_final,
        mock_transcript=req.mock_transcript,
    )

    return AudioStreamChunkResponse(**result.model_dump())


@router.websocket("/ws/{session_id}/{speaker_id}")
@router.websocket("/ws")
async def audio_stream_websocket(
    websocket: WebSocket,
    session_id: str = "session_default",
    speaker_id: str = "speaker_default",
):
    """Real-time bidirectional WebSocket stream for continuous PCM audio frames."""
    await websocket.accept()
    pipeline = get_streaming_pipeline()

    qp = websocket.query_params
    sess_id = qp.get("session_id") or session_id
    spk_id = qp.get("speaker_id") or speaker_id
    spk_name = qp.get("speaker_name") or "Player"
    camp_id = qp.get("campaign_id") or sess_id

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            audio_bytes = b""
            is_final = False
            mock_transcript = None
            sample_rate = 16000

            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    b64 = payload.get("audio_data") or payload.get("audio_base64")
                    if b64:
                        audio_bytes = base64.b64decode(b64)
                    spk_name = payload.get("speaker_name") or spk_name
                    spk_id = payload.get("speaker_id") or spk_id
                    sess_id = payload.get("session_id") or sess_id
                    camp_id = payload.get("campaign_id") or camp_id
                    is_final = bool(payload.get("is_final", False))
                    mock_transcript = payload.get("mock_transcript")
                    sample_rate = int(payload.get("sample_rate", 16000))
                except Exception as exc:
                    logger.warning("Failed to parse WebSocket JSON audio frame: %s", exc)
                    continue

            result = await pipeline.process_chunk(
                session_id=sess_id,
                speaker_id=spk_id,
                speaker_name=spk_name,
                campaign_id=camp_id,
                audio_bytes=audio_bytes,
                sample_rate=sample_rate,
                is_final=is_final,
                mock_transcript=mock_transcript,
            )

            await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        logger.debug("Voice stream WebSocket disconnected for %s:%s", sess_id, spk_id)
