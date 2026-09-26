"""Signaling connection manager for active WebRTC voice rooms."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from fastapi import WebSocket
from voice_agent.room import (
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
)

logger = logging.getLogger("runefoble.gateway.signaling.manager")


class WebRTCSignalingManager:
    """Manages active WebRTC signaling WebSocket connections per audio room."""

    def __init__(self, coordinator: VoiceRoomCoordinator | None = None) -> None:
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

__all__ = ["WebRTCSignalingManager", "signaling_manager"]
