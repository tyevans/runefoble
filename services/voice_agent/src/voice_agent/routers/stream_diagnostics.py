"""Diagnostic API endpoints for WebRTC stream quality and adaptive bitrate (TASK-0166)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from runefoble_events.voice_stream_quality import (
    VoiceStreamCodecAdaptedEvent,
    VoiceStreamQualityDegradedEvent,
)
from voice_agent.dependencies import publish_voice_event
from voice_agent.webrtc.adaptive_bitrate import AdaptiveBitrateRegulator
from voice_agent.webrtc.models import RTCPReportRequest, StreamQualityResponse
from voice_agent.webrtc.quality_monitor import NetworkQualityMonitor

router = APIRouter(tags=["Voice Stream Diagnostics"])
_qm = NetworkQualityMonitor()
_abr = AdaptiveBitrateRegulator()


def get_quality_monitor() -> NetworkQualityMonitor:
    return _qm


def get_bitrate_regulator() -> AdaptiveBitrateRegulator:
    return _abr


def reset_diagnostics() -> None:
    _qm.reset()
    _abr.reset()


def _make_resp(
    sid: str, pid: str, adapted: bool = False, reason: str = "nominal"
) -> StreamQualityResponse:
    m, p = _qm.get_peer_quality(sid, pid), _abr.get_current_params(sid, pid)
    return StreamQualityResponse(
        session_id=sid,
        peer_id=pid,
        bitrate_kbps=p.bitrate_kbps,
        packet_loss=m.packet_loss if m else 0.0,
        codec_mode=p.codec_mode,
        sample_rate=p.sample_rate,
        channels=p.channels,
        complexity=p.complexity,
        fec_enabled=p.fec_enabled,
        dtx_enabled=p.dtx_enabled,
        rtt_ms=m.rtt_ms if m else 0.0,
        jitter_ms=m.jitter_ms if m else 0.0,
        is_degraded=m.is_degraded if m else False,
        severity=m.severity if m else "nominal",
        detection_latency_ms=m.detection_latency_ms if m else 0.0,
        adapted=adapted,
        reason=reason,
    )


@router.get("/voice/streams/{session_id}/quality")
@router.get("/api/v1/voice/streams/{session_id}/quality")
async def get_stream_quality(session_id: str, peer_id: str | None = None) -> Any:
    """Query stream bitrate, packet loss, and codec mode."""
    if peer_id:
        return _make_resp(session_id, peer_id)
    return {
        "session_id": session_id,
        "streams": [_make_resp(session_id, p) for p in _qm.get_session_qualities(session_id)],
    }


@router.post("/voice/streams/{session_id}/report", response_model=StreamQualityResponse)
@router.post("/voice/streams/{session_id}/quality", response_model=StreamQualityResponse)
@router.post("/api/v1/voice/streams/{session_id}/report", response_model=StreamQualityResponse)
async def submit_rtcp_report(session_id: str, req: RTCPReportRequest) -> StreamQualityResponse:
    """Submit RTCP report, evaluate degradation, and adapt Opus bitrate."""
    prev = _abr.get_current_params(session_id, req.peer_id)
    m = _qm.analyze_report(session_id, req.peer_id, req.model_dump())
    if m.is_degraded:
        await publish_voice_event(
            VoiceStreamQualityDegradedEvent(
                session_id=session_id,
                peer_id=req.peer_id,
                user_id=req.user_id,
                packet_loss=m.packet_loss,
                round_trip_time_ms=m.rtt_ms,
                jitter_ms=m.jitter_ms,
                severity=m.severity,
            )
        )
    p, changed, reason = _abr.regulate(session_id, req.peer_id, m.packet_loss, m.rtt_ms)
    if changed:
        await publish_voice_event(
            VoiceStreamCodecAdaptedEvent(
                session_id=session_id,
                peer_id=req.peer_id,
                user_id=req.user_id,
                previous_bitrate_kbps=prev.bitrate_kbps,
                new_bitrate_kbps=p.bitrate_kbps,
                sample_rate=p.sample_rate,
                channels=p.channels,
                complexity=p.complexity,
                fec_enabled=p.fec_enabled,
                dtx_enabled=p.dtx_enabled,
                codec_mode=p.codec_mode,
                reason=reason,
            )
        )
    return _make_resp(session_id, req.peer_id, adapted=changed, reason=reason)


__all__ = [
    "RTCPReportRequest",
    "StreamQualityResponse",
    "get_bitrate_regulator",
    "get_quality_monitor",
    "reset_diagnostics",
    "router",
]
