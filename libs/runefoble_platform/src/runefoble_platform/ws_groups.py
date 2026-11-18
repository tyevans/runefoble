"""Keyed WebSocket groups: register, leave, broadcast, and prune dead peers.

One registry holds the live sockets of one room kind, for example one session, campaign,
table, or board. A broadcast reaches every live socket in the named group. A socket whose
send fails is logged and removed from the group. The other sockets still receive the message.

The registry keeps state in one process. With more than one replica, a broadcast reaches only
the sockets that this replica holds.
"""

from __future__ import annotations

import logging
from collections.abc import Hashable
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("runefoble.platform.ws_groups")


class WebSocketGroups[K: Hashable]:
    """Admitted WebSocket connections, grouped by a room key."""

    def __init__(self) -> None:
        self._groups: dict[K, list[WebSocket]] = {}

    def register(self, key: K, websocket: WebSocket) -> None:
        """Track an admitted, accepted socket. The route accepts it first."""
        self._groups.setdefault(key, []).append(websocket)

    def disconnect(self, key: K, websocket: WebSocket) -> None:
        """Remove a socket from its group. An unknown socket or group is ignored."""
        group = self._groups.get(key)
        if group is None:
            return
        if websocket in group:
            group.remove(websocket)
        if not group:
            del self._groups[key]

    async def broadcast(self, key: K, message: dict[str, Any]) -> None:
        """Send `message` to every live socket in the group. Prune each socket whose send fails."""
        for websocket in list(self._groups.get(key, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 - one dead peer must not stop the fan-out
                logger.warning(
                    "Pruned a WebSocket from group %r after a failed send", key, exc_info=True
                )
                self.disconnect(key, websocket)

    def clear(self) -> None:
        """Drop every group. Use it to reset a process-wide registry between tests."""
        self._groups.clear()


__all__ = ["WebSocketGroups"]
