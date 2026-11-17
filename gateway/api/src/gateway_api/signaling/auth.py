"""Signaling Zanzibar authorization and peer metadata extraction.

The subject comes from the verified principal. Query parameters only carry
presentation fields (peer id and role). They never carry identity.
"""

from __future__ import annotations

from fastapi import WebSocket
from runefoble_auth.spicedb import SpiceDBClient


def extract_peer_and_role(websocket: WebSocket, user_id: str) -> tuple[str, str]:
    """Return (peer_id, role) for an admitted subject."""
    peer_id = websocket.query_params.get("peer_id") or f"peer_{user_id}"
    role = websocket.query_params.get("role") or "player"
    return peer_id, role


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

    # Check campaign-level permissions. The schema unions owner, DM, GM, and player into these.
    for perm in ("play", "view", "run_session", "manage"):
        if await spicedb.check_permission("campaign", session_id, perm, "user", subject_id):
            return True

    return False


__all__ = ["extract_peer_and_role", "validate_voice_connection"]
