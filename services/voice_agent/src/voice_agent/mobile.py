"""Mobile Companion Low-Bandwidth Audio Profiles and Haptic Protocol.

Governed by ADR-0002, ADR-0005, and ADR-0013.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class HapticVibrationPattern:
    """Pre-defined standard haptic vibration patterns (in milliseconds)."""

    SECRET_WHISPER: list[int] = [200, 100, 200]
    TURN_ALERT: list[int] = [300, 150, 300]
    CRITICAL_ALERT: list[int] = [100, 50, 100, 50, 200]
    DANGER_ALERT: list[int] = [500]
    HEARTBEAT: list[int] = [100, 200, 100]

    @classmethod
    def get_pattern(cls, alert_type: str) -> list[int]:
        mapping = {
            "secret_whisper": cls.SECRET_WHISPER,
            "turn_alert": cls.TURN_ALERT,
            "critical_alert": cls.CRITICAL_ALERT,
            "danger_alert": cls.DANGER_ALERT,
            "heartbeat": cls.HEARTBEAT,
        }
        return mapping.get(alert_type, cls.SECRET_WHISPER)


class MobileAudioProfileTier(StrEnum):
    """Audio profile tiers for mobile WebRTC / WebSocket streaming."""

    STANDARD = "standard"
    MOBILE_OPTIMIZED = "mobile_optimized"
    CELLULAR_CONSTRAINED = "cellular_constrained"
    ULTRA_LOW = "ultra_low"


class MobileAudioProfile(BaseModel):
    """Configuration profile for adaptive Opus mobile streaming."""

    tier: str = MobileAudioProfileTier.MOBILE_OPTIMIZED
    codec: str = "opus"
    sample_rate: int = 16000
    channels: int = 1
    bitrate_kbps: int = 16
    frame_duration_ms: int = 20
    fec_enabled: bool = True
    dtx_enabled: bool = True
    packet_loss_concealment: bool = True
    complexity: int = Field(default=5, ge=0, le=10)


def _prof(tier: str, rate: int, br: int, fec: bool, comp: int) -> MobileAudioProfile:
    return MobileAudioProfile(
        tier=tier,
        sample_rate=rate,
        channels=1,
        bitrate_kbps=br,
        fec_enabled=fec,
        dtx_enabled=fec,
        complexity=comp,
    )


PROFILES: dict[str, MobileAudioProfile] = {
    MobileAudioProfileTier.STANDARD: _prof(MobileAudioProfileTier.STANDARD, 48000, 48, False, 8),
    MobileAudioProfileTier.MOBILE_OPTIMIZED: _prof(
        MobileAudioProfileTier.MOBILE_OPTIMIZED, 16000, 16, True, 5
    ),
    MobileAudioProfileTier.CELLULAR_CONSTRAINED: _prof(
        MobileAudioProfileTier.CELLULAR_CONSTRAINED, 16000, 12, True, 4
    ),
    MobileAudioProfileTier.ULTRA_LOW: _prof(MobileAudioProfileTier.ULTRA_LOW, 16000, 8, True, 3),
}


def adapt_audio_profile(
    packet_loss: float = 0.0,
    bandwidth_kbps: float | None = None,
    latency_ms: float | None = None,
) -> tuple[MobileAudioProfile, str]:
    """Adapt mobile audio stream profile based on real-time network conditions."""
    if packet_loss >= 0.15:
        return PROFILES[MobileAudioProfileTier.ULTRA_LOW], "severe_packet_loss"
    if bandwidth_kbps is not None and bandwidth_kbps < 25.0:
        return PROFILES[MobileAudioProfileTier.ULTRA_LOW], "severely_constrained_bandwidth"
    if packet_loss >= 0.05:
        return PROFILES[MobileAudioProfileTier.CELLULAR_CONSTRAINED], "high_packet_loss"
    if bandwidth_kbps is not None and bandwidth_kbps < 50.0:
        return (
            PROFILES[MobileAudioProfileTier.CELLULAR_CONSTRAINED],
            "constrained_cellular_bandwidth",
        )
    if latency_ms is not None and latency_ms > 300.0:
        return PROFILES[MobileAudioProfileTier.CELLULAR_CONSTRAINED], "high_latency_jitter"
    return PROFILES[MobileAudioProfileTier.MOBILE_OPTIMIZED], "nominal_cellular"


def create_diegetic_whisper_notification(
    content: str,
    sender: str = "The Watcher",
    character_name: str | None = None,
    is_secret: bool = True,
) -> dict[str, Any]:
    """Create diegetic lockscreen / notification card payload for a secret whisper."""
    title = (
        f"{sender} whispers..."
        if not character_name
        else f"{sender} whispers to {character_name}..."
    )
    return {
        "title": title,
        "body": content,
        "diegetic": True,
        "urgent": True,
        "is_secret": is_secret,
        "sender": sender,
        "character_name": character_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "actions": [
            {"action": "dismiss", "title": "Acknowledge"},
            {"action": "reply_whisper", "title": "Whisper Back"},
        ],
    }


def create_turn_alert_notification(
    character_name: str,
    round_num: int | None = None,
) -> dict[str, Any]:
    """Create urgent lockscreen alert for combat turn initiative."""
    body = (
        f"It's {character_name}'s turn to act in round {round_num}!"
        if round_num
        else f"It's {character_name}'s turn in combat!"
    )
    return {
        "title": "Your Combat Turn!",
        "body": body,
        "diegetic": True,
        "urgent": True,
        "turn_alert": True,
        "character_name": character_name,
        "round": round_num,
        "timestamp": datetime.now(UTC).isoformat(),
        "actions": [
            {"action": "view_board", "title": "Open Board"},
            {"action": "pass_turn", "title": "End Turn"},
        ],
    }


def create_haptic_payload(
    session_id: str,
    alert_type: str = "secret_whisper",
    custom_pattern: list[int] | None = None,
    whisper: dict[str, Any] | None = None,
    notification: dict[str, Any] | None = None,
    recipient_id: str | None = None,
) -> dict[str, Any]:
    """Format standard WebSocket haptic ping frame for mobile companions."""
    pattern = custom_pattern or HapticVibrationPattern.get_pattern(alert_type)
    return {
        "type": "haptic_ping",
        "ping_id": f"ping-{uuid4().hex[:8]}",
        "session_id": session_id,
        "recipient_id": recipient_id,
        "alert_type": alert_type,
        "vibration_pattern": pattern,
        "whisper": whisper,
        "notification": notification,
        "timestamp": datetime.now(UTC).isoformat(),
    }


__all__ = [
    "HapticVibrationPattern",
    "MobileAudioProfile",
    "MobileAudioProfileTier",
    "PROFILES",
    "adapt_audio_profile",
    "create_diegetic_whisper_notification",
    "create_haptic_payload",
    "create_turn_alert_notification",
]
