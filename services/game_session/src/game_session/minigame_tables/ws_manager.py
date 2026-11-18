"""WebSocket connection registry for multiplayer minigame tables.

Holds only live socket connections. Table game state is event-sourced on the
TavernGame aggregate (TASK-0566), so a restart loses no table state.
"""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class MinigameTableManager:
    """Tracks admitted WebSocket connections per table and broadcasts messages."""

    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = {}

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
        sockets = list(self.connections.get(table_id, set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(table_id, ws)


minigame_table_manager = MinigameTableManager()
