"""WebSocket Voice Duplex Signaling and Interruption Router (TASK-0141).

Notifies clients and The Watcher of barge-in state transitions and halts TTS playback < 100ms.
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from runefoble_auth.websocket import admit_websocket
from runefoble_platform.event_publish import publish_best_effort
from voice_agent.auth import CallerPrincipal, get_voice_verifier
from voice_agent.authz import require_action, speaker_authorizer
from voice_agent.barge_in import BargeInDetector
from voice_agent.coordinator import VoiceRoomCoordinator, get_voice_room_coordinator
from voice_agent.dependencies import STREAM_SESSION, STREAM_VOICE, get_event_bus
from voice_agent.echo_canceller import AcousticEchoCanceller
from voice_agent.models import PlaybackStartRequest

logger = logging.getLogger("runefoble.voice_agent.duplex")
router = APIRouter(prefix="/api/v1/voice/duplex", tags=["Voice Duplex & Interruption"])


@router.post("/playback/start")
async def start_playback(req: PlaybackStartRequest, principal: CallerPrincipal):
    await require_action("session.participate", req.session_id, principal.user_id)
    await get_voice_room_coordinator().start_playback(
        req.session_id, req.playback_id, req.text, req.duration_ms
    )
    return {"status": "started", "playback_id": req.playback_id, "session_id": req.session_id}


@router.get("/status/{session_id}")
async def get_playback_status(session_id: str, principal: CallerPrincipal):
    await require_action("session.observe", session_id, principal.user_id)
    active = await get_voice_room_coordinator().playback_active(session_id)
    return {"session_id": session_id, "playback_active": active}


async def _handle_interruption(
    coord: VoiceRoomCoordinator,
    sess_id: str,
    spk_id: str,
    spk_name: str,
    pcm: bytes,
    latency: float,
    ws: WebSocket,
) -> bool:
    """Stop the stored playback on speech. Return False when no playback is active."""
    res = await coord.interrupt_playback(sess_id, spk_id, spk_name, audio_tail=pcm)
    if res is None:
        return False
    ev = res.to_event()
    bus = get_event_bus()
    for s in (STREAM_VOICE, STREAM_SESSION):
        await publish_best_effort(bus, s, ev)

    frames = [
        {
            "type": "barge_in_detected",
            "session_id": sess_id,
            "speaker_id": spk_id,
            "cutoff_ms": res.cutoff_position_ms,
            "remaining_text": res.remaining_narration_text,
            "latency_ms": latency,
        },
        {"type": "webrtc_stream_mute", "stream_id": "tts_playback", "is_muted": True},
        {
            "type": "playback_canceled",
            "playback_id": res.playback_id,
            "remaining_narration_text": res.remaining_narration_text,
        },
    ]
    for frame in frames:
        await ws.send_json(frame)
    return True


@router.websocket("/ws/{session_id}/{speaker_id}")
@router.websocket("/ws")
async def duplex_websocket(
    websocket: WebSocket, session_id: str = "default", speaker_id: str = "default"
):
    qp = websocket.query_params
    sess_id = qp.get("session_id") or session_id
    spk_id = qp.get("speaker_id") or speaker_id
    spk_name = qp.get("speaker_name") or "Player"
    if (
        await admit_websocket(websocket, get_voice_verifier(), speaker_authorizer(sess_id, spk_id))
        is None
    ):
        return

    barge_in, aec = BargeInDetector(), AcousticEchoCanceller()
    coord = get_voice_room_coordinator()
    await websocket.send_json(
        {"type": "voice_duplex_connected", "session_id": sess_id, "speaker_id": spk_id}
    )
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            mic_bytes = msg.get("bytes") or b""
            if not mic_bytes and "text" in msg and msg["text"]:
                p = json.loads(msg["text"])
                if p.get("type") == "playback_start":
                    await coord.start_playback(
                        sess_id,
                        p.get("playback_id", "pb-1"),
                        p.get("text", ""),
                        p.get("duration_ms", 10000.0),
                    )
                    await websocket.send_json(
                        {"type": "playback_started", "playback_id": p.get("playback_id")}
                    )
                    continue
                elif p.get("type") == "speaker_audio":
                    aec.register_speaker_output(base64.b64decode(p.get("audio_data", "")))
                    continue
                elif p.get("type") == "mic_audio":
                    mic_bytes = base64.b64decode(p.get("audio_data", ""))

            if not mic_bytes:
                continue
            if aec.is_echo_dominant(mic_bytes):
                await websocket.send_json({"type": "echo_suppressed", "speech_detected": False})
                continue
            clean_pcm = aec.filter_echo(mic_bytes)
            det = barge_in.analyze_chunk(clean_pcm)
            handled = det.is_interrupted and await _handle_interruption(
                coord, sess_id, spk_id, spk_name, clean_pcm, det.onset_latency_ms, websocket
            )
            if not handled:
                await websocket.send_json(
                    {
                        "type": "duplex_state",
                        "speech_detected": det.speech_frames_count > 0,
                        "confidence": det.confidence,
                    }
                )
    except WebSocketDisconnect:
        logger.debug("Duplex WebSocket disconnected: %s", sess_id)


__all__ = ["duplex_websocket", "router"]
