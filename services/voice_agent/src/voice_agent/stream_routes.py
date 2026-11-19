"""HTTP and WebSocket routes for live audio streaming, VAD, and Whisper transcription."""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from runefoble_auth.websocket import (
    WS_AUTHORIZATION_REFUSED,
    WS_POLICY_VIOLATION,
    admit_websocket,
    bearer_token_from_subprotocols,
    send_socket_error,
)
from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.event_publish import DomainEventPublishError
from voice_agent.auth import CallerPrincipal, get_voice_verifier
from voice_agent.authz import require_speaker, speaker_allowed, speaker_authorizer
from voice_agent.stream_frames import (
    FRAME_PARSE_ERRORS,
    AudioFrame,
    StreamContext,
    parse_text_frame,
)
from voice_agent.stt import get_streaming_pipeline
from voice_agent.vad import AudioFormatError

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
    # Why The Watcher did not take the transcript. None when it answered (TASK-0732).
    watcher_error: str | None = None
    vad_state: str = "silence"
    buffer_duration_ms: float = 0.0


@router.post("/chunk", response_model=AudioStreamChunkResponse)
async def ingest_audio_chunk(
    req: AudioStreamChunkRequest,
    principal: CallerPrincipal,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """Ingest PCM/WAV audio chunk, process VAD boundaries, and trigger streaming transcription."""
    await require_speaker(req.session_id, req.speaker_id, principal.user_id)
    raw_b64 = req.audio_data or req.audio_base64
    audio_bytes = b""
    if raw_b64:
        try:
            audio_bytes = base64.b64decode(raw_b64)
        except binascii.Error as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 audio payload: {e}",
            ) from e

    # EngineUnavailableError becomes HTTP 503 in the app exception handler.
    result = await get_streaming_pipeline().process_chunk(
        session_id=req.session_id,
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        campaign_id=req.campaign_id,
        audio_bytes=audio_bytes,
        sample_rate=req.sample_rate,
        is_whisper=req.is_whisper,
        target_character_id=req.target_character_id,
        is_final=req.is_final,
        caller_authorization=authorization,
    )

    return AudioStreamChunkResponse(**result.model_dump())


REQUIRED_QUERY_VALUES = ("campaign_id", "speaker_name")


@router.websocket("/ws/{session_id}/{speaker_id}")
async def audio_stream_websocket(websocket: WebSocket, session_id: str, speaker_id: str):
    """Real-time bidirectional WebSocket stream for continuous PCM audio frames.

    The query must name `campaign_id` and `speaker_name`. A missing value gets an
    `INVALID_REQUEST` error frame, and the socket closes with 1008.
    """
    principal = await admit_websocket(
        websocket, get_voice_verifier(), speaker_authorizer(session_id, speaker_id)
    )
    if principal is None:
        return
    qp = websocket.query_params
    missing = [name for name in REQUIRED_QUERY_VALUES if not qp.get(name)]
    if missing:
        await send_socket_error(
            websocket, "INVALID_REQUEST", f"Missing query value: {', '.join(missing)}"
        )
        await websocket.close(code=WS_POLICY_VIOLATION)
        return
    context = StreamContext(
        session_id=session_id,
        speaker_id=speaker_id,
        speaker_name=qp["speaker_name"],
        campaign_id=qp["campaign_id"],
    )
    pipeline = get_streaming_pipeline()
    token = bearer_token_from_subprotocols(list(websocket.scope.get("subprotocols", [])))
    caller_authorization = f"Bearer {token}" if token else None
    verified_pairs = {(session_id, speaker_id)}

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("bytes"):
                frame = AudioFrame(context=context, audio_bytes=message["bytes"])
            elif message.get("text"):
                try:
                    frame = parse_text_frame(message["text"], context)
                except FRAME_PARSE_ERRORS as exc:
                    # The frame is not forwarded. Tell the client, then keep the stream open.
                    await send_socket_error(websocket, "INVALID_FRAME", str(exc))
                    continue
            else:
                frame = AudioFrame(context=context)
            context = frame.context

            # A frame may name another session or speaker. Each new pair needs its own check.
            pair = (context.session_id, context.speaker_id)
            if pair not in verified_pairs:
                if not await speaker_allowed(*pair, principal.user_id):
                    logger.warning(
                        "Voice stream frame names a speaker the principal may not act for"
                    )
                    await websocket.close(code=WS_AUTHORIZATION_REFUSED)
                    break
                verified_pairs.add(pair)

            try:
                result = await pipeline.process_chunk(
                    session_id=context.session_id,
                    speaker_id=context.speaker_id,
                    speaker_name=context.speaker_name,
                    campaign_id=context.campaign_id,
                    audio_bytes=frame.audio_bytes,
                    sample_rate=frame.sample_rate,
                    is_final=frame.is_final,
                    caller_authorization=caller_authorization,
                )
            except AudioFormatError as e:
                # The frame is not forwarded. Tell the client, then keep the stream open.
                await websocket.send_json({"error": e.error_code, "message": str(e)})
                continue
            except EngineUnavailableError as e:
                await websocket.send_json(e.body())
                continue
            except DomainEventPublishError as e:
                # The chunk is not recorded. Tell the client, then keep the stream open.
                await websocket.send_json(
                    {"status": "publish_failed", "event_type": e.event_type, "detail": str(e)}
                )
                continue

            await websocket.send_json(result.model_dump())
    except WebSocketDisconnect:
        logger.debug(
            "Voice stream WebSocket disconnected for %s:%s",
            context.session_id,
            context.speaker_id,
        )
