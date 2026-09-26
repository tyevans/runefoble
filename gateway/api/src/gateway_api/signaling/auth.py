"""Signaling Zanzibar authorization and credential extraction."""

from __future__ import annotations

from fastapi import WebSocket
from runefoble_auth.spicedb import SpiceDBClient


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


__all__ = ["extract_signaling_auth", "validate_voice_connection"]
