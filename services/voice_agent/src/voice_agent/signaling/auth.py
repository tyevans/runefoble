"""Signaling Zanzibar authorization and peer metadata extraction.

The subject comes from the verified principal. Query parameters only carry
presentation fields (peer id and role). They never carry identity.
"""

from __future__ import annotations

from fastapi import WebSocket


def extract_peer_and_role(websocket: WebSocket, user_id: str) -> tuple[str, str]:
    """Return (peer_id, role) for an admitted subject."""
    peer_id = websocket.query_params.get("peer_id") or f"peer_{user_id}"
    role = websocket.query_params.get("role") or "player"
    return peer_id, role


__all__ = ["extract_peer_and_role"]
