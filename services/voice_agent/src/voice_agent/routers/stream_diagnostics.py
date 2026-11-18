"""Diagnostic API endpoints for WebRTC stream quality and adaptive bitrate (TASK-0166).

Quality measurements and codec parameters live in the voice room aggregate (TASK-0577).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from runefoble_events.events import (
    VoiceStreamCodecAdaptedEvent,
    VoiceStreamQualityDegradedEvent,
)
from voice_agent.auth import CallerPrincipal, get_principal
from voice_agent.authz import require_action
from voice_agent.coordinator import get_voice_room_coordinator
from voice_agent.dependencies import publish_voice_event
from voice_agent.room_aggregate import PeerStreamState
from voice_agent.webrtc.models import RTCPReportRequest, StreamQualityResponse

router = APIRouter(dependencies=[Depends(get_principal)], tags=["Voice Stream Diagnostics"])


def _make_resp(
    sid: str,
    pid: str,
    stream: PeerStreamState | None,
    adapted: bool = False,
    reason: str = "nominal",
) -> StreamQualityResponse:
    s = stream or PeerStreamState()
    p = s.codec
    return StreamQualityResponse(
        session_id=sid,
        peer_id=pid,
        bitrate_kbps=p.bitrate_kbps,
        packet_loss=s.packet_loss,
        codec_mode=p.codec_mode,
        sample_rate=p.sample_rate,
        channels=p.channels,
        complexity=p.complexity,
        fec_enabled=p.fec_enabled,
        dtx_enabled=p.dtx_enabled,
        rtt_ms=s.rtt_ms,
        jitter_ms=s.jitter_ms,
        is_degraded=s.is_degraded,
        severity=s.severity,
        detection_latency_ms=s.detection_latency_ms,
        adapted=adapted,
        reason=reason,
    )


@router.get("/voice/streams/{session_id}/quality")
@router.get("/api/v1/voice/streams/{session_id}/quality")
async def get_stream_quality(
    session_id: str, principal: CallerPrincipal, peer_id: str | None = None
) -> Any:
    """Query stream bitrate, packet loss, and codec mode."""
    await require_action("session.control", session_id, principal.user_id)
    streams = await get_voice_room_coordinator().stream_states(session_id)
    if peer_id:
        return _make_resp(session_id, peer_id, streams.get(peer_id))
    return {
        "session_id": session_id,
        "streams": [_make_resp(session_id, pid, s) for pid, s in streams.items()],
    }


@router.post("/voice/streams/{session_id}/report", response_model=StreamQualityResponse)
@router.post("/voice/streams/{session_id}/quality", response_model=StreamQualityResponse)
@router.post("/api/v1/voice/streams/{session_id}/report", response_model=StreamQualityResponse)
async def submit_rtcp_report(
    session_id: str, req: RTCPReportRequest, principal: CallerPrincipal
) -> StreamQualityResponse:
    """Submit RTCP report, evaluate degradation, and adapt Opus bitrate."""
    await require_action("session.control", session_id, principal.user_id)
    outcome = await get_voice_room_coordinator().record_stream_report(
        session_id, principal.user_id, req
    )
    m, codec = outcome.metrics, outcome.codec
    if m.is_degraded:
        await publish_voice_event(
            VoiceStreamQualityDegradedEvent(
                session_id=session_id,
                peer_id=req.peer_id,
                user_id=principal.user_id,
                packet_loss=m.packet_loss,
                round_trip_time_ms=m.rtt_ms,
                jitter_ms=m.jitter_ms,
                severity=m.severity,
            )
        )
    if outcome.adapted:
        await publish_voice_event(
            VoiceStreamCodecAdaptedEvent(
                session_id=session_id,
                peer_id=req.peer_id,
                user_id=principal.user_id,
                previous_bitrate_kbps=outcome.previous_bitrate_kbps,
                new_bitrate_kbps=codec.bitrate_kbps,
                sample_rate=codec.sample_rate,
                channels=codec.channels,
                complexity=codec.complexity,
                fec_enabled=codec.fec_enabled,
                dtx_enabled=codec.dtx_enabled,
                codec_mode=codec.codec_mode,
                reason=outcome.reason,
            )
        )
    return _make_resp(
        session_id,
        req.peer_id,
        PeerStreamState(
            packet_loss=m.packet_loss,
            rtt_ms=m.rtt_ms,
            jitter_ms=m.jitter_ms,
            is_degraded=m.is_degraded,
            severity=m.severity,
            detection_latency_ms=m.detection_latency_ms,
            codec=codec,
        ),
        adapted=outcome.adapted,
        reason=outcome.reason,
    )


__all__ = [
    "RTCPReportRequest",
    "StreamQualityResponse",
    "router",
]
