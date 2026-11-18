"""Signaling peer id extraction.

The subject comes from the verified principal, and the role comes from the session
permissions (`voice_agent.signaling.role`). The query parameter `peer_id` is the only
presentation field that a client sends at admission. It never carries identity or role.
"""

from __future__ import annotations

from fastapi import WebSocket


def extract_peer_id(websocket: WebSocket, user_id: str) -> str:
    """Return the peer id for an admitted subject."""
    return websocket.query_params.get("peer_id") or f"peer_{user_id}"


__all__ = ["extract_peer_id"]
