"""Session object permission checks for gateway HTTP routes (ADR-0001).

Every check uses a permission that `runefoble.zed` defines on the `game_session` object:
`observe` for reads, `participate` for player actions, and `control` for DM actions.
Socket admission uses `runefoble_auth.websocket.admit_websocket` with `action_authorizer`.
"""

from __future__ import annotations

from fastapi import HTTPException, WebSocket
from gateway_api.auth import get_spicedb_client
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.websocket import send_socket_error


async def has_session_permission(session_id: str, user_id: str, permission: str) -> bool:
    """Return whether the user holds `permission` on the session. May raise AuthzUnavailableError."""
    return await get_spicedb_client().check_permission(
        resource_type="game_session",
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


async def may_publish_frame(
    websocket: WebSocket, session_id: str, user_id: str, action: str, permission: str
) -> bool:
    """Return whether an inbound socket frame may reach the room (TASK-0810, TASK-0910).

    The caller names the `game_session` permission that the frame kind needs. A refused caller
    gets a `PERMISSION_DENIED` frame, and the frame is not relayed. A SpiceDB outage gets
    `AUTHZ_UNAVAILABLE`, and the frame is not relayed either. Both the session and the overlay
    sockets call this check.
    """
    try:
        allowed = await has_session_permission(session_id, user_id, permission)
    except AuthzUnavailableError:
        await send_socket_error(
            websocket, "AUTHZ_UNAVAILABLE", "Authorization unavailable", action=action
        )
        return False
    if not allowed:
        await send_socket_error(
            websocket,
            "PERMISSION_DENIED",
            f"Action '{action}' needs session.{permission}",
            action=action,
        )
    return allowed


__all__ = ["has_session_permission", "may_publish_frame", "require_session_permission"]
