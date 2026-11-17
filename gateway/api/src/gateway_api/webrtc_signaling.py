"""Backward-compatible facade for WebRTC voice room signaling.

Re-exports WebRTCSignalingManager, signaling_manager, extract_peer_and_role,
validate_voice_connection, and voice_signaling_websocket_endpoint from gateway_api.signaling.
"""

from __future__ import annotations

import logging

from gateway_api.signaling import (
    WebRTCSignalingManager,
    extract_peer_and_role,
    signaling_manager,
    validate_voice_connection,
    voice_signaling_websocket_endpoint,
)

logger = logging.getLogger("runefoble.gateway.webrtc_signaling")

__all__ = [
    "WebRTCSignalingManager",
    "extract_peer_and_role",
    "logger",
    "signaling_manager",
    "validate_voice_connection",
    "voice_signaling_websocket_endpoint",
]
