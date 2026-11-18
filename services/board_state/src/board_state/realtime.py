"""WebSocket connection registry for live board broadcasts, kept separate from route maths."""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import WebSocket


class BoardWebSocketManager:
    """Manages active live WebSocket connections per board / session."""

    def __init__(self) -> None:
        self.active_rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self.active_rooms:
            self.active_rooms[session_id] = []
        self.active_rooms[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.active_rooms:
            with contextlib.suppress(ValueError):
                self.active_rooms[session_id].remove(websocket)
            if not self.active_rooms[session_id]:
                del self.active_rooms[session_id]

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        if session_id not in self.active_rooms:
            return
        dead_connections: list[WebSocket] = []
        for connection in self.active_rooms[session_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(session_id, dead)


board_ws_manager = BoardWebSocketManager()
