"""WebRTC RTCP Receiver Report Network Quality Monitor.

Analyzes RTCP receiver reports to detect packet loss and round-trip delay spikes.
Governed by ADR-0002, ADR-0003, and ADR-0006.
"""

from __future__ import annotations

import time
from typing import Any

from voice_agent.webrtc.models import QualityMetrics, RTCPReceiverReport


class NetworkQualityMonitor:
    """Detects packet loss (>5%) and RTT spikes from RTCP receiver reports within 100ms."""

    def __init__(
        self,
        loss_threshold: float = 0.05,
        severe_loss_threshold: float = 0.15,
        rtt_threshold_ms: float = 250.0,
        severe_rtt_threshold_ms: float = 400.0,
    ) -> None:
        self.loss_threshold = loss_threshold
        self.severe_loss_threshold = severe_loss_threshold
        self.rtt_threshold_ms = rtt_threshold_ms
        self.severe_rtt_threshold_ms = severe_rtt_threshold_ms
        self._states: dict[tuple[str, str], QualityMetrics] = {}

    def analyze_report(
        self,
        session_id: str,
        peer_id: str,
        report: RTCPReceiverReport | dict[str, Any],
    ) -> QualityMetrics:
        """Analyze receiver report and return evaluated stream quality within 100ms."""
        t0 = time.perf_counter()
        rep = RTCPReceiverReport(**report) if isinstance(report, dict) else report

        loss = rep.packet_loss
        if rep.fraction_lost is not None and rep.fraction_lost > 0:
            loss = rep.fraction_lost / 256.0 if rep.fraction_lost > 1.0 else rep.fraction_lost
        elif loss > 1.0:
            loss = loss / 100.0

        rtt, jitter = rep.rtt_ms, rep.jitter_ms
        is_severe = loss >= self.severe_loss_threshold or rtt >= self.severe_rtt_threshold_ms
        is_degraded = loss >= self.loss_threshold or rtt >= self.rtt_threshold_ms

        if is_severe:
            severity = "severe"
        elif is_degraded:
            severity = "degraded"
        else:
            severity = "nominal"

        duration_ms = (time.perf_counter() - t0) * 1000.0
        metrics = QualityMetrics(
            peer_id=peer_id,
            packet_loss=round(loss, 4),
            rtt_ms=round(rtt, 2),
            jitter_ms=round(jitter, 2),
            is_degraded=is_degraded,
            severity=severity,
            detection_latency_ms=round(duration_ms, 3),
            analyzed_at=time.time(),
        )
        self._states[(session_id, peer_id)] = metrics
        return metrics

    def get_peer_quality(self, session_id: str, peer_id: str) -> QualityMetrics | None:
        """Retrieve latest quality metrics for a given peer in a session."""
        return self._states.get((session_id, peer_id))

    def get_session_qualities(self, session_id: str) -> dict[str, QualityMetrics]:
        """Retrieve latest quality metrics for all peers in a session."""
        return {pid: m for (sid, pid), m in self._states.items() if sid == session_id}

    def reset(self, session_id: str | None = None, peer_id: str | None = None) -> None:
        """Clear cached metrics for specific peer, session, or all."""
        if session_id and peer_id:
            self._states.pop((session_id, peer_id), None)
        elif session_id:
            keys = [k for k in self._states if k[0] == session_id]
            for k in keys:
                self._states.pop(k, None)
        else:
            self._states.clear()


__all__ = ["NetworkQualityMonitor", "QualityMetrics", "RTCPReceiverReport"]
