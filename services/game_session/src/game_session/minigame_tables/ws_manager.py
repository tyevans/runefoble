"""WebSocket connection registry for multiplayer minigame tables.

Holds only live socket connections. Table game state is event-sourced on the
TavernGame aggregate (TASK-0566), so a restart loses no table state.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketDisconnected

logger = logging.getLogger("runefoble.game_session.minigame_tables")

# Errors that mean the peer has closed its socket. The socket is removed from the table.
CLOSED_SOCKET_ERRORS: tuple[type[BaseException], ...] = (
    WebSocketDisconnect,
    WebSocketDisconnected,
)


class MinigameTableManager:
    """Tracks admitted WebSocket connections per table and broadcasts messages."""

    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}
        self.send_failures = 0

    def register(self, table_id: str, websocket: WebSocket) -> None:
        """Track an admitted, accepted socket. The route accepts it first."""
        if table_id not in self.connections:
            self.connections[table_id] = set()
        self.connections[table_id].add(websocket)

    def disconnect(self, table_id: str, websocket: WebSocket) -> None:
        if table_id in self.connections:
            self.connections[table_id].discard(websocket)
            if not self.connections[table_id]:
                del self.connections[table_id]

    async def broadcast(self, table_id: str, message: dict[str, Any]) -> None:
        """Send `message` to every socket on the table.

        A closed socket is removed. Any other send failure is logged and counted in
        `send_failures`. The socket stays registered, and the other sockets still receive
        the message.
        """
        sockets = list(self.connections.get(table_id, set()))
        closed: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except CLOSED_SOCKET_ERRORS:
                closed.append(ws)
            except Exception:
                self.send_failures += 1
                logger.exception("Minigame table %s: send to a live socket failed", table_id)
        for ws in closed:
            self.disconnect(table_id, ws)


minigame_table_manager = MinigameTableManager()
