"""WebRTC voice signaling WebSocket endpoint."""

from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect
from voice_agent.auth import get_voice_verifier
from voice_agent.signaling.auth import extract_peer_and_role
from voice_agent.signaling.handlers import (
    SignalingPeerState,
    dispatch_signaling_message,
    handle_peer_disconnect,
)
from voice_agent.signaling.manager import WebRTCSignalingManager, signaling_manager
from voice_agent.socket_access import admit_session_socket

logger = logging.getLogger("runefoble.voice_agent.signaling.endpoint")


async def voice_signaling_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: WebRTCSignalingManager | None = None,
) -> None:
    """Handle WebRTC voice room signaling WebSocket at /ws/voice/{session_id}."""
    principal = await admit_session_socket(
        websocket, get_voice_verifier(), session_id, "session.observe"
    )
    if principal is None:
        return
    user_id = principal.user_id
    sig_manager = manager or signaling_manager
    coord = sig_manager.coordinator
    peer_id, role = extract_peer_and_role(websocket, user_id)

    await sig_manager.connect_peer(session_id, peer_id, websocket)

    # 2. Register peer joining the voice room aggregate
    await coord.peer_joined(session_id, peer_id, user_id, role)

    # 3. Send initial connected and room summary confirmation
    room_summary = await coord.get_room_summary(session_id)
    await websocket.send_json(
        {
            "type": "connected",
            "session_id": session_id,
            "peer_id": peer_id,
            "user_id": user_id,
            "role": role,
            "message": "Connected to Runefoble WebRTC voice signaling room.",
        }
    )
    await websocket.send_json(
        {
            "type": "webrtc_joined",
            "session_id": session_id,
            "peer_id": peer_id,
            "user_id": user_id,
            "role": role,
            "peers": room_summary["participants"],
        }
    )

    # Broadcast arrival to existing room members
    await sig_manager.broadcast_to_room(
        session_id,
        {
            "type": "webrtc_peer_joined",
            "session_id": session_id,
            "peer_id": peer_id,
            "user_id": user_id,
            "role": role,
        },
        exclude_peer=peer_id,
    )

    state = SignalingPeerState(
        session_id=session_id,
        peer_id=peer_id,
        user_id=user_id,
        role=role,
    )

    try:
        while True:
            data = await websocket.receive_json()
            should_continue = await dispatch_signaling_message(websocket, state, data, sig_manager)
            if not should_continue:
                return
    except WebSocketDisconnect:
        await handle_peer_disconnect(websocket, sig_manager)


__all__ = ["voice_signaling_websocket_endpoint"]
