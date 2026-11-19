"""Session permission dependencies for the lifecycle routes (TASK-0767).

Each dependency checks one permission of the `session` definition in
libs/runefoble_auth/schema/runefoble.zed for the verified caller and returns the caller id.
No role name or token claim grants access here (ADR-0001, ADR-0015).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from game_session.settlement.auth.tokens import CallerId, CallerOrService
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import require_subject


def session_permission(permission: str) -> Callable[..., Awaitable[str]]:
    """Build a dependency that requires `permission` on the `session_id` path parameter."""

    async def dependency(session_id: UUID, caller_id: CallerId) -> str:
        await require_subject(
            get_spicedb_client(),
            "session",
            str(session_id),
            permission,
            caller_id,
            detail=f"User '{caller_id}' lacks '{permission}' on session '{session_id}'",
        )
        return caller_id

    return dependency


SessionController = Annotated[str, Depends(session_permission("control"))]
SessionParticipant = Annotated[str, Depends(session_permission("participate"))]
SessionObserver = Annotated[str, Depends(session_permission("observe"))]


async def session_reader(session_id: UUID, caller: CallerOrService) -> str | None:
    """Require `session.observe` for a user caller. A service call with no user passes.

    The service credential is a trusted internal caller (ADR-0015). A user, or a service call on
    behalf of a user, must hold the permission.
    """
    if caller.user_id is None:
        return None
    return await session_permission("observe")(session_id, caller.user_id)


SessionReader = Depends(session_reader)
