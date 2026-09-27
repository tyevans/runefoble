"""Adaptive Bitrate Regulator for WebRTC Opus Voice Streaming.

Regulates Opus encoder bitrate, sample rate, and complexity dynamically based on RTCP feedback.
Governed by ADR-0002, ADR-0003, and ADR-0006.
"""

from __future__ import annotations

from voice_agent.webrtc.models import OpusCodecParameters

TIER_PROFILES: dict[str, OpusCodecParameters] = {
    "standard": OpusCodecParameters(
        bitrate_kbps=48, complexity=8, fec_enabled=False, codec_mode="standard"
    ),
    "mobile_optimized": OpusCodecParameters(
        bitrate_kbps=24, complexity=5, fec_enabled=True, codec_mode="mobile_optimized"
    ),
    "cellular_constrained": OpusCodecParameters(
        bitrate_kbps=12, complexity=4, fec_enabled=True, codec_mode="cellular_constrained"
    ),
    "ultra_low": OpusCodecParameters(
        bitrate_kbps=8, complexity=3, fec_enabled=True, codec_mode="ultra_low"
    ),
}


class AdaptiveBitrateRegulator:
    """Dynamically steps Opus audio parameters down to 16kHz mono (<50 kbps) under packet loss."""

    def __init__(
        self,
        loss_threshold: float = 0.05,
        severe_loss_threshold: float = 0.15,
        recovery_loss_threshold: float = 0.02,
        rtt_threshold_ms: float = 250.0,
        severe_rtt_threshold_ms: float = 400.0,
        recovery_rtt_threshold_ms: float = 120.0,
    ) -> None:
        self.loss_threshold = loss_threshold
        self.severe_loss_threshold = severe_loss_threshold
        self.recovery_loss_threshold = recovery_loss_threshold
        self.rtt_threshold_ms = rtt_threshold_ms
        self.severe_rtt_threshold_ms = severe_rtt_threshold_ms
        self.recovery_rtt_threshold_ms = recovery_rtt_threshold_ms
        self._states: dict[tuple[str, str], OpusCodecParameters] = {}

    def get_current_params(self, session_id: str, peer_id: str) -> OpusCodecParameters:
        """Get active Opus encoder parameters for given peer, defaulting to standard."""
        return self._states.get((session_id, peer_id), TIER_PROFILES["standard"].model_copy())

    def regulate(
        self,
        session_id: str,
        peer_id: str,
        packet_loss: float,
        rtt_ms: float = 0.0,
    ) -> tuple[OpusCodecParameters, bool, str]:
        """Evaluate network conditions and adjust Opus codec parameters."""
        current = self.get_current_params(session_id, peer_id)

        if packet_loss >= self.severe_loss_threshold or rtt_ms >= self.severe_rtt_threshold_ms:
            target_key = "ultra_low"
            reason = (
                "severe_packet_loss"
                if packet_loss >= self.severe_loss_threshold
                else "severe_rtt_latency"
            )
        elif packet_loss >= self.loss_threshold or rtt_ms >= self.rtt_threshold_ms:
            target_key = "cellular_constrained"
            reason = (
                "packet_loss_exceeded_threshold"
                if packet_loss >= self.loss_threshold
                else "rtt_delay_spike"
            )
        elif (
            packet_loss <= self.recovery_loss_threshold
            and rtt_ms <= self.recovery_rtt_threshold_ms
            and current.codec_mode != "standard"
        ):
            target_key = "standard"
            reason = "network_condition_recovered"
        else:
            return current, False, "nominal_stability"

        target = TIER_PROFILES[target_key].model_copy()
        changed = (
            target.bitrate_kbps != current.bitrate_kbps
            or target.complexity != current.complexity
            or target.codec_mode != current.codec_mode
        )
        if changed:
            self._states[(session_id, peer_id)] = target
        return target, changed, reason

    def reset(self, session_id: str | None = None, peer_id: str | None = None) -> None:
        """Reset codec state for specific peer or session."""
        if session_id and peer_id:
            self._states.pop((session_id, peer_id), None)
        elif session_id:
            keys = [k for k in self._states if k[0] == session_id]
            for k in keys:
                self._states.pop(k, None)
        else:
            self._states.clear()


__all__ = ["TIER_PROFILES", "AdaptiveBitrateRegulator", "OpusCodecParameters"]
