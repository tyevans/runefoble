"""WebRTC signaling message dispatchers and disconnect handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket

if TYPE_CHECKING:
    from gateway_api.signaling.manager import WebRTCSignalingManager


@dataclass
class SignalingPeerState:
    """State for an active signaling connection."""

    session_id: str
    peer_id: str
    user_id: str
    role: str


async def handle_join(
    websocket: WebSocket,
    state: SignalingPeerState,
    data: dict[str, Any],
    manager: WebRTCSignalingManager,
) -> None:
    """Handle explicit join re-confirmation or credential refresh."""
    req_peer = data.get("peer_id", state.peer_id)
    req_user = data.get("user_id", state.user_id)
    req_role = data.get("role", state.role)
    if req_peer != state.peer_id:
        manager.disconnect_peer(websocket)
        state.peer_id = req_peer
        await manager.connect_peer(state.session_id, state.peer_id, websocket)
        await manager.coordinator.peer_joined(state.session_id, state.peer_id, req_user, req_role)

    state.user_id, state.role = req_user, req_role
    summary = await manager.coordinator.get_room_summary(state.session_id)
    await websocket.send_json(
        {
            "type": "webrtc_joined",
            "session_id": state.session_id,
            "peer_id": state.peer_id,
            "user_id": req_user,
            "role": req_role,
            "peers": summary["participants"],
        }
    )
    await manager.broadcast_to_room(
        state.session_id,
        {
            "type": "webrtc_peer_joined",
            "session_id": state.session_id,
            "peer_id": state.peer_id,
            "user_id": req_user,
            "role": req_role,
        },
        exclude_peer=state.peer_id,
    )


async def handle_sdp_and_ice(
    state: SignalingPeerState,
    data: dict[str, Any],
    msg_type: str,
    manager: WebRTCSignalingManager,
) -> None:
    """Relay SDP offer, SDP answer, or trickle ICE candidate to target peer or room."""
    target_peer = data.get("to_peer") or data.get("target_peer")
    from_p = data.get("from_peer") or state.peer_id
    payload = {
        "type": msg_type,
        "from_peer": from_p,
        "to_peer": target_peer,
        **{
            k: v
            for k, v in data.items()
            if k not in ("type", "action", "from_peer", "to_peer", "target_peer")
        },
    }
    if target_peer:
        await manager.send_to_peer(state.session_id, target_peer, payload)
    else:
        await manager.broadcast_to_room(state.session_id, payload, exclude_peer=from_p)


async def handle_mute(
    state: SignalingPeerState,
    data: dict[str, Any],
    manager: WebRTCSignalingManager,
) -> None:
    """Toggle mute state and broadcast update to room."""
    is_muted = bool(data.get("is_muted", True))
    await manager.coordinator.mute_toggled(state.session_id, state.peer_id, is_muted)
    await manager.broadcast_to_room(
        state.session_id,
        {
            "type": "webrtc_peer_muted",
            "session_id": state.session_id,
            "peer_id": state.peer_id,
            "is_muted": is_muted,
        },
    )


async def handle_telemetry(
    state: SignalingPeerState,
    data: dict[str, Any],
    manager: WebRTCSignalingManager,
) -> None:
    """Update participant audio telemetry and broadcast to peers."""
    manager.coordinator.update_telemetry(
        session_id=state.session_id,
        peer_id=state.peer_id,
        audio_level=data.get("audio_level"),
        latency_ms=data.get("latency_ms"),
        is_speaking=data.get("is_speaking"),
    )
    await manager.broadcast_to_room(
        state.session_id,
        {
            "type": "webrtc_telemetry",
            "session_id": state.session_id,
            "peer_id": state.peer_id,
            "audio_level": data.get("audio_level", 0.0),
            "latency_ms": data.get("latency_ms", 0.0),
            "is_speaking": data.get("is_speaking", False),
        },
        exclude_peer=state.peer_id,
    )


async def handle_leave(
    websocket: WebSocket,
    state: SignalingPeerState,
    data: dict[str, Any],
    manager: WebRTCSignalingManager,
) -> None:
    """Handle graceful audio room departure."""
    reason = data.get("reason", "left_session")
    manager.disconnect_peer(websocket)
    await manager.coordinator.peer_left(state.session_id, state.peer_id, reason=reason)
    await manager.broadcast_to_room(
        state.session_id,
        {
            "type": "webrtc_peer_left",
            "session_id": state.session_id,
            "peer_id": state.peer_id,
            "reason": reason,
        },
    )
    await websocket.close(code=1000, reason="Graceful audio leave")


async def handle_peer_disconnect(websocket: WebSocket, manager: WebRTCSignalingManager) -> None:
    """Clean up state on abrupt peer WebSocket disconnection."""
    info = manager.disconnect_peer(websocket)
    if info:
        s_id, p_id = info
        await manager.coordinator.peer_left(s_id, p_id, reason="disconnected")
        await manager.broadcast_to_room(
            s_id,
            {
                "type": "webrtc_peer_left",
                "session_id": s_id,
                "peer_id": p_id,
                "reason": "disconnected",
            },
        )


async def dispatch_signaling_message(
    websocket: WebSocket,
    state: SignalingPeerState,
    data: dict[str, Any],
    manager: WebRTCSignalingManager,
) -> bool:
    """Dispatch inbound signaling message. Returns False if session ended."""
    msg_type = data.get("type") or data.get("action") or "unknown"
    if msg_type == "webrtc_join":
        await handle_join(websocket, state, data, manager)
    elif msg_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice_candidate"):
        await handle_sdp_and_ice(state, data, msg_type, manager)
    elif msg_type in ("webrtc_mute", "webrtc_mute_toggle"):
        await handle_mute(state, data, manager)
    elif msg_type == "webrtc_telemetry":
        await handle_telemetry(state, data, manager)
    elif msg_type == "webrtc_leave":
        await handle_leave(websocket, state, data, manager)
        return False
    return True


__all__ = [
    "SignalingPeerState",
    "dispatch_signaling_message",
    "handle_join",
    "handle_leave",
    "handle_mute",
    "handle_peer_disconnect",
    "handle_sdp_and_ice",
    "handle_telemetry",
]
