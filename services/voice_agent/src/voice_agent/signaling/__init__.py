"""Modular WebRTC voice room signaling package for Runefoble Gateway."""

from __future__ import annotations

from voice_agent.signaling.auth import (
    extract_peer_id,
)
from voice_agent.signaling.endpoint import (
    voice_signaling_websocket_endpoint,
)
from voice_agent.signaling.handlers import (
    SignalingPeerState,
    dispatch_signaling_message,
    handle_join,
    handle_leave,
    handle_mute,
    handle_peer_disconnect,
    handle_sdp_and_ice,
    handle_telemetry,
)
from voice_agent.signaling.manager import (
    WebRTCSignalingManager,
    signaling_manager,
)

__all__ = [
    "SignalingPeerState",
    "WebRTCSignalingManager",
    "dispatch_signaling_message",
    "extract_peer_id",
    "handle_join",
    "handle_leave",
    "handle_mute",
    "handle_peer_disconnect",
    "handle_sdp_and_ice",
    "handle_telemetry",
    "signaling_manager",
    "voice_signaling_websocket_endpoint",
]
