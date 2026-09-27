"""Data models for WebRTC stream quality and Opus adaptive bitrate."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field


class RTCPReceiverReport(BaseModel):
    """WebRTC RTCP Receiver Report block metrics."""

    ssrc: int | None = None
    packet_loss: float = 0.0
    fraction_lost: float | None = None
    cumulative_lost: int = 0
    extended_highest_seq: int = 0
    jitter_ms: float = 0.0
    rtt_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class RTCPReportRequest(BaseModel):
    """HTTP payload for reporting client RTCP receiver telemetry."""

    peer_id: str
    user_id: str | None = None
    packet_loss: float = 0.0
    fraction_lost: float | None = None
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    ssrc: int | None = None


class QualityMetrics(BaseModel):
    """Evaluated network quality metrics for a voice stream peer."""

    peer_id: str
    packet_loss: float
    rtt_ms: float
    jitter_ms: float
    is_degraded: bool
    severity: str = "nominal"
    detection_latency_ms: float = 0.0
    analyzed_at: float = Field(default_factory=time.time)


class OpusCodecParameters(BaseModel):
    """Dynamic Opus encoder configuration parameters."""

    codec: str = "opus"
    sample_rate: int = 16000
    channels: int = 1
    bitrate_kbps: int = 48
    complexity: int = Field(default=8, ge=0, le=10)
    fec_enabled: bool = True
    dtx_enabled: bool = True
    frame_duration_ms: int = 20
    codec_mode: str = "standard"


class StreamQualityResponse(BaseModel):
    """Response payload for stream diagnostics and bitrate inquiries."""

    session_id: str
    peer_id: str
    bitrate_kbps: int
    packet_loss: float
    codec_mode: str
    sample_rate: int = 16000
    channels: int = 1
    complexity: int = 8
    fec_enabled: bool = True
    dtx_enabled: bool = True
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    is_degraded: bool = False
    severity: str = "nominal"
    detection_latency_ms: float = 0.0
    adapted: bool = False
    reason: str = "nominal"


__all__ = [
    "OpusCodecParameters",
    "QualityMetrics",
    "RTCPReceiverReport",
    "RTCPReportRequest",
    "StreamQualityResponse",
]
