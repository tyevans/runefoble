"""Session role of an admitted voice peer, decided by SpiceDB (TASK-0811, ADR-0015 c).

The role is a label for the room. It never grants access. Each label comes from one schema
permission on the session: `session.control` gives the DM role, `session.participate` gives
the player role, and `session.observe` gives the spectator role. A client frame or query
parameter never sets the role.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket
from runefoble_auth.errors import AuthzError
from runefoble_auth.websocket import (
    WS_AUTHORIZATION_REFUSED,
    WS_AUTHORIZATION_UNAVAILABLE,
)
from voice_agent.authz import action_allowed

logger = logging.getLogger("runefoble.voice_agent.signaling.role")

ROLE_DUNGEON_MASTER = "dungeon_master"
ROLE_PLAYER = "player"
ROLE_SPECTATOR = "spectator"


async def resolve_session_role(session_id: str, user_id: str) -> str | None:
    """Return the highest role that the session permissions grant, or None when none applies.

    A SpiceDB failure raises `AuthzError`. A failed check is never a denial.
    """
    if await action_allowed("session.control", session_id, user_id):
        return ROLE_DUNGEON_MASTER
    if await action_allowed("session.participate", session_id, user_id):
        return ROLE_PLAYER
    if await action_allowed("session.observe", session_id, user_id):
        return ROLE_SPECTATOR
    return None


async def admitted_session_role(websocket: WebSocket, session_id: str, user_id: str) -> str | None:
    """Resolve the role of an admitted socket. On refusal or failure, close it and return None.

    Close codes follow `runefoble_auth.websocket`: 4403 when no session role applies, and
    1011 when SpiceDB cannot answer.
    """
    try:
        role = await resolve_session_role(session_id, user_id)
    except AuthzError:
        logger.error("Voice session role unavailable on %s", websocket.url.path)
        await websocket.close(code=WS_AUTHORIZATION_UNAVAILABLE, reason="Authorization unavailable")
        return None
    if role is None:
        logger.warning("Voice socket refused on %s: no session role", websocket.url.path)
        await websocket.close(code=WS_AUTHORIZATION_REFUSED, reason="Forbidden")
    return role


__all__ = [
    "ROLE_DUNGEON_MASTER",
    "ROLE_PLAYER",
    "ROLE_SPECTATOR",
    "admitted_session_role",
    "resolve_session_role",
]
