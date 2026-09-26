"""WebRTC voice signaling WebSocket endpoint."""

from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.auth import get_spicedb_client
from gateway_api.signaling.auth import extract_signaling_auth, validate_voice_connection
from gateway_api.signaling.handlers import (
    SignalingPeerState,
    dispatch_signaling_message,
    handle_peer_disconnect,
)
from gateway_api.signaling.manager import WebRTCSignalingManager, signaling_manager

logger = logging.getLogger("runefoble.gateway.signaling.endpoint")


async def voice_signaling_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: WebRTCSignalingManager | None = None,
) -> None:
    """Handle WebRTC voice room signaling WebSocket at /ws/voice/{session_id}."""
    sig_manager = manager or signaling_manager
    coord = sig_manager.coordinator
    spicedb = get_spicedb_client()

    user_id, peer_id, role = extract_signaling_auth(websocket)

    # 1. SpiceDB Zanzibar permission check on connect (Hard Invariant 1)
    can_connect = await validate_voice_connection(spicedb, session_id, user_id)
    if not can_connect:
        logger.warning(
            "Voice WebSocket connect rejected: subject '%s' lacks permissions for session '%s'",
            user_id,
            session_id,
        )
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "code": "PERMISSION_DENIED",
                "message": (
                    f"Zanzibar authorization denied: insufficient permissions to join voice room "
                    f"for session '{session_id}'"
                ),
                "action": "connect",
            }
        )
        await websocket.close(
            code=4003, reason="Forbidden: insufficient permissions for voice room"
        )
        return

    await websocket.accept()
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
