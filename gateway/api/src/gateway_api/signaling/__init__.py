"""Modular WebRTC voice room signaling package for Runefoble Gateway."""

from __future__ import annotations

from gateway_api.signaling.auth import (
    extract_signaling_auth,
    validate_voice_connection,
)
from gateway_api.signaling.endpoint import (
    voice_signaling_websocket_endpoint,
)
from gateway_api.signaling.handlers import (
    SignalingPeerState,
    dispatch_signaling_message,
    handle_join,
    handle_leave,
    handle_mute,
    handle_peer_disconnect,
    handle_sdp_and_ice,
    handle_telemetry,
)
from gateway_api.signaling.manager import (
    WebRTCSignalingManager,
    signaling_manager,
)

__all__ = [
    "SignalingPeerState",
    "WebRTCSignalingManager",
    "dispatch_signaling_message",
    "extract_signaling_auth",
    "handle_join",
    "handle_leave",
    "handle_mute",
    "handle_peer_disconnect",
    "handle_sdp_and_ice",
    "handle_telemetry",
    "signaling_manager",
    "validate_voice_connection",
    "voice_signaling_websocket_endpoint",
]
