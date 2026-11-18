"""Session object permission checks for gateway sockets and routes (ADR-0001).

Every check uses a permission that `runefoble.zed` defines on the `session` object:
`observe` for reads, `participate` for player actions, and `control` for DM actions.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, WebSocket
from gateway_api.auth import get_spicedb_client
from runefoble_auth.errors import AuthzUnavailableError

logger = logging.getLogger("runefoble.gateway.session_access")

FORBIDDEN_CLOSE_CODE = 4403
UNAVAILABLE_CLOSE_CODE = 1011


async def has_session_permission(session_id: str, user_id: str, permission: str) -> bool:
    """Return whether the user holds `permission` on the session. May raise AuthzUnavailableError."""
    return await get_spicedb_client().check_permission(
        resource_type="session",
        resource_id=session_id,
        permission=permission,
        subject_type="user",
        subject_id=user_id,
    )


async def require_session_permission(session_id: str, user_id: str, permission: str) -> None:
    """Raise 403 unless the user holds `permission` on the session, or 503 when SpiceDB is down."""
    try:
        allowed = await has_session_permission(session_id, user_id, permission)
    except AuthzUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"error": "authz_unavailable"}) from exc
    if not allowed:
        raise HTTPException(status_code=403, detail={"error": "permission_denied"})


async def socket_may(websocket: WebSocket, session_id: str, user_id: str, permission: str) -> bool:
    """Check a session permission on connect. Close the socket and return False when refused."""
    try:
        allowed = await has_session_permission(session_id, user_id, permission)
    except AuthzUnavailableError:
        logger.error("Authorization unavailable for socket on session '%s'", session_id)
        await websocket.close(code=UNAVAILABLE_CLOSE_CODE, reason="Authorization unavailable")
        return False
    if not allowed:
        logger.warning("Socket refused: '%s' lacks %s on '%s'", user_id, permission, session_id)
        await websocket.close(code=FORBIDDEN_CLOSE_CODE, reason=f"Forbidden: needs {permission}")
        return False
    return True


__all__ = [
    "FORBIDDEN_CLOSE_CODE",
    "UNAVAILABLE_CLOSE_CODE",
    "has_session_permission",
    "require_session_permission",
    "socket_may",
]
