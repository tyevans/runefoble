"""Live overlay sockets and the per-socket feed state.

The room holds sockets only. It keeps no session or board state. Each broadcast goes to the
sockets of one session.
"""

from __future__ import annotations

from dataclasses import dataclass

from runefoble_platform.ws_groups import WebSocketGroups

# Live spectator sockets, one WebSocket group per session. Holds no domain state.
ws_overlay_manager = WebSocketGroups[str]()


@dataclass
class OverlayFeed:
    """Per-socket state: the caller's bearer, forwarded to the owners on each relay."""

    authorization: str | None = None


__all__ = ["OverlayFeed", "ws_overlay_manager"]
