"""Session object permission checks for gateway HTTP routes (ADR-0001).

Every check uses a permission that `runefoble.zed` defines on the `session` object:
`observe` for reads, `participate` for player actions, and `control` for DM actions.
Socket admission uses `runefoble_auth.websocket.admit_websocket` with `action_authorizer`.
"""

from __future__ import annotations

from fastapi import HTTPException
from gateway_api.auth import get_spicedb_client
from runefoble_auth.errors import AuthzUnavailableError


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


__all__ = ["has_session_permission", "require_session_permission"]
