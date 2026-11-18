"""Session permission gate for voice_agent WebSockets (TASK-0544 checks, now owned here).

The gateway relays the signaling and companion sockets to this service. The gateway holds no
socket state, so the session check runs here. It uses the same schema permission that
TASK-0544 set. The check runs after the handshake is verified and accepted.
Refusals close the accepted socket with the code that the client receives:
- 4403: the subject lacks the permission.
- 1011: SpiceDB is unavailable. Authorization failure is never a denial.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket
from runefoble_auth.errors import AuthzError
from runefoble_auth.principal import BearerVerifier, VerifiedPrincipal
from runefoble_auth.websocket import admit_websocket
from voice_agent.authz import action_allowed

logger = logging.getLogger("runefoble.voice_agent.socket_access")

FORBIDDEN_CLOSE_CODE = 4403
UNAVAILABLE_CLOSE_CODE = 1011


async def admit_session_socket(
    websocket: WebSocket,
    verifier: BearerVerifier,
    session_id: str,
    action: str,
) -> VerifiedPrincipal | None:
    """Verify and accept the handshake, then check `action` on the session. None when refused."""
    principal = await admit_websocket(websocket, verifier)
    if principal is None:
        return None
    try:
        allowed = await action_allowed(action, session_id, principal.user_id)
    except AuthzError:
        logger.error("Authorization unavailable for socket on session '%s'", session_id)
        await websocket.close(code=UNAVAILABLE_CLOSE_CODE, reason="Authorization unavailable")
        return None
    if not allowed:
        logger.warning(
            "Socket refused: '%s' lacks %s on '%s'", principal.user_id, action, session_id
        )
        await websocket.close(code=FORBIDDEN_CLOSE_CODE, reason=f"Forbidden: needs {action}")
        return None
    return principal


__all__ = ["FORBIDDEN_CLOSE_CODE", "UNAVAILABLE_CLOSE_CODE", "admit_session_socket"]
