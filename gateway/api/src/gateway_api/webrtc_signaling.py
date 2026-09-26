"""Live WebRTC Bidirectional Voice Room Signaling Gateway.

Handles WebSocket connections for WebRTC peer signaling (join, offer, answer,
ICE candidates, mute toggles, and DM moderation) with SpiceDB Zanzibar enforcement.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.auth import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from voice_agent.room import (
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
)

logger = logging.getLogger("runefoble.gateway.webrtc_signaling")


class WebRTCSignalingManager:
    """Manages active WebRTC signaling WebSocket connections per audio room."""

    def __init__(self, coordinator: VoiceRoomCoordinator | None = None):
        self._coordinator = coordinator
        self.active_rooms: dict[
            str, dict[str, WebSocket]
        ] = {}  # session_id -> peer_id -> WebSocket
        self.peer_sessions: dict[WebSocket, tuple[str, str]] = {}  # ws -> (session_id, peer_id)

        # Wire kick listener to gracefully terminate kicked peer WebSocket connections
        coord = self.coordinator
        coord.register_kick_callback(self.handle_peer_kicked)

    @property
    def coordinator(self) -> VoiceRoomCoordinator:
        coord = self._coordinator or get_voice_room_coordinator()
        if self.handle_peer_kicked not in coord._kick_callbacks:
            coord.register_kick_callback(self.handle_peer_kicked)
        return coord

    async def connect_peer(
        self,
        session_id: str,
        peer_id: str,
        websocket: WebSocket,
    ) -> None:
        if session_id not in self.active_rooms:
            self.active_rooms[session_id] = {}
        self.active_rooms[session_id][peer_id] = websocket
        self.peer_sessions[websocket] = (session_id, peer_id)

    def disconnect_peer(self, websocket: WebSocket) -> tuple[str, str] | None:
        if websocket not in self.peer_sessions:
            return None
        session_id, peer_id = self.peer_sessions.pop(websocket)
        if session_id in self.active_rooms:
            self.active_rooms[session_id].pop(peer_id, None)
            if not self.active_rooms[session_id]:
                del self.active_rooms[session_id]
        return session_id, peer_id

    async def broadcast_to_room(
        self,
        session_id: str,
        message: dict[str, Any],
        exclude_peer: str | None = None,
    ) -> None:
        peers = list(self.active_rooms.get(session_id, {}).items())
        for pid, ws in peers:
            if pid != exclude_peer:
                with contextlib.suppress(Exception):
                    await ws.send_json(message)

    async def send_to_peer(
        self,
        session_id: str,
        target_peer_id: str,
        message: dict[str, Any],
    ) -> bool:
        ws = self.active_rooms.get(session_id, {}).get(target_peer_id)
        if ws:
            with contextlib.suppress(Exception):
                await ws.send_json(message)
                return True
        return False

    async def handle_peer_kicked(
        self,
        session_id: str,
        peer_id: str,
        reason: str,
    ) -> None:
        ws = self.active_rooms.get(session_id, {}).get(peer_id)
        if ws:
            with contextlib.suppress(Exception):
                await ws.send_json(
                    {
                        "type": "webrtc_kicked",
                        "session_id": session_id,
                        "peer_id": peer_id,
                        "reason": reason,
                    }
                )
                await ws.close(code=4001, reason=f"Kicked by DM: {reason}")
            self.disconnect_peer(ws)

        await self.broadcast_to_room(
            session_id,
            {
                "type": "webrtc_peer_left",
                "session_id": session_id,
                "peer_id": peer_id,
                "reason": reason,
            },
            exclude_peer=peer_id,
        )


signaling_manager = WebRTCSignalingManager()


def extract_signaling_auth(websocket: WebSocket) -> tuple[str, str, str]:
    """Extract authenticated (subject_id, peer_id, role) from WebSocket query params or headers."""
    # Subject / User ID
    user_id = None
    for param in ("user_id", "x_user_id", "subject_id", "token"):
        val = websocket.query_params.get(param)
        if val:
            user_id = val
            break
    if not user_id:
        user_id = websocket.headers.get("x-user-id")
    if not user_id:
        auth = websocket.headers.get("authorization")
        if auth and auth.startswith("Bearer "):
            user_id = auth[7:].strip()
    if not user_id:
        user_id = "guest_user"

    # Peer ID
    peer_id = websocket.query_params.get("peer_id") or f"peer_{user_id}"

    # Role
    role = websocket.query_params.get("role") or "player"

    return user_id, peer_id, role


async def validate_voice_connection(
    spicedb: SpiceDBClient,
    session_id: str,
    subject_id: str,
) -> bool:
    """Verify viewer/subject has permission to access voice room in SpiceDB Zanzibar."""
    # Check session-level permissions
    for perm in ("participate", "observe", "control"):
        if await spicedb.check_permission("game_session", session_id, perm, "user", subject_id):
            return True
        if await spicedb.check_permission("session", session_id, perm, "user", subject_id):
            return True

    # Check campaign-level permissions
    for perm in (
        "play",
        "view",
        "read",
        "run_session",
        "owner",
        "manage",
        "dungeon_master",
        "player",
    ):
        if await spicedb.check_permission("campaign", session_id, perm, "user", subject_id):
            return True

    return False


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

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type") or data.get("action") or "unknown"

            if msg_type == "webrtc_join":
                # Explicit join re-confirmation or credential refresh
                req_peer = data.get("peer_id", peer_id)
                req_user = data.get("user_id", user_id)
                req_role = data.get("role", role)
                if req_peer != peer_id:
                    sig_manager.disconnect_peer(websocket)
                    peer_id = req_peer
                    await sig_manager.connect_peer(session_id, peer_id, websocket)
                    await coord.peer_joined(session_id, peer_id, req_user, req_role)

                summary = await coord.get_room_summary(session_id)
                await websocket.send_json(
                    {
                        "type": "webrtc_joined",
                        "session_id": session_id,
                        "peer_id": peer_id,
                        "user_id": req_user,
                        "role": req_role,
                        "peers": summary["participants"],
                    }
                )
                await sig_manager.broadcast_to_room(
                    session_id,
                    {
                        "type": "webrtc_peer_joined",
                        "session_id": session_id,
                        "peer_id": peer_id,
                        "user_id": req_user,
                        "role": req_role,
                    },
                    exclude_peer=peer_id,
                )

            elif msg_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice_candidate"):
                target_peer = data.get("to_peer") or data.get("target_peer")
                from_p = data.get("from_peer") or peer_id
                payload = {
                    "type": msg_type,
                    "from_peer": from_p,
                    "to_peer": target_peer,
                    **{
                        k: v
                        for k, v in data.items()
                        if k not in ("type", "from_peer", "to_peer", "target_peer")
                    },
                }
                if target_peer:
                    await sig_manager.send_to_peer(session_id, target_peer, payload)
                else:
                    await sig_manager.broadcast_to_room(session_id, payload, exclude_peer=from_p)

            elif msg_type in ("webrtc_mute", "webrtc_mute_toggle"):
                is_muted = bool(data.get("is_muted", True))
                await coord.mute_toggled(session_id, peer_id, is_muted)
                await sig_manager.broadcast_to_room(
                    session_id,
                    {
                        "type": "webrtc_peer_muted",
                        "session_id": session_id,
                        "peer_id": peer_id,
                        "is_muted": is_muted,
                    },
                )

            elif msg_type == "webrtc_telemetry":
                coord.update_telemetry(
                    session_id=session_id,
                    peer_id=peer_id,
                    audio_level=data.get("audio_level"),
                    latency_ms=data.get("latency_ms"),
                    is_speaking=data.get("is_speaking"),
                )
                await sig_manager.broadcast_to_room(
                    session_id,
                    {
                        "type": "webrtc_telemetry",
                        "session_id": session_id,
                        "peer_id": peer_id,
                        "audio_level": data.get("audio_level", 0.0),
                        "latency_ms": data.get("latency_ms", 0.0),
                        "is_speaking": data.get("is_speaking", False),
                    },
                    exclude_peer=peer_id,
                )

            elif msg_type == "webrtc_leave":
                reason = data.get("reason", "left_session")
                sig_manager.disconnect_peer(websocket)
                await coord.peer_left(session_id, peer_id, reason=reason)
                await sig_manager.broadcast_to_room(
                    session_id,
                    {
                        "type": "webrtc_peer_left",
                        "session_id": session_id,
                        "peer_id": peer_id,
                        "reason": reason,
                    },
                )
                await websocket.close(code=1000, reason="Graceful audio leave")
                return

    except WebSocketDisconnect:
        info = sig_manager.disconnect_peer(websocket)
        if info:
            s_id, p_id = info
            await coord.peer_left(s_id, p_id, reason="disconnected")
            await sig_manager.broadcast_to_room(
                s_id,
                {
                    "type": "webrtc_peer_left",
                    "session_id": s_id,
                    "peer_id": p_id,
                    "reason": "disconnected",
                },
            )
