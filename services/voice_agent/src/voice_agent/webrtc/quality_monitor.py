"""WebRTC RTCP Receiver Report Network Quality Monitor.

Analyzes RTCP receiver reports to detect packet loss and round-trip delay spikes.
Governed by ADR-0002, ADR-0003, and ADR-0006.
"""

from __future__ import annotations

import time
from typing import Any

from voice_agent.webrtc.models import QualityMetrics, RTCPReceiverReport


class NetworkQualityMonitor:
    """Detects packet loss (>5%) and RTT spikes from RTCP receiver reports within 100ms.

    The monitor holds thresholds only. Each report is evaluated on its own. The room aggregate
    stores the result (TASK-0577).
    """

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

    def analyze_report(
        self,
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
        return metrics


__all__ = ["NetworkQualityMonitor", "QualityMetrics", "RTCPReceiverReport"]
