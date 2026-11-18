"""Board permission checks against the SpiceDB `board` schema (ADR-0001).

Every check names a schema permission of `definition board` in `runefoble.zed`. No role name
appears here. `board.campaign` links a board to its campaign. Creation writes that tuple.
A SpiceDB failure raises `AuthzError`. The app maps it to 503 or 500 and never to a denial.
"""

from __future__ import annotations

from board_state.dependencies import to_board_uuid
from fastapi import HTTPException, status
from runefoble_auth.factory import get_spicedb_client

MANAGE_TRAPS = "manage_traps"
VIEW_SECRET_LAYER = "view_secret_layer"
SWITCH_MAP = "switch_map"


def board_resource_id(session_id: str) -> str:
    """Return the SpiceDB object id of the board for a session id."""
    return str(to_board_uuid(session_id))


async def can_on_board(user_id: str | None, session_id: str, permission: str) -> bool:
    """Return whether the user holds a board permission. A service call has no user and holds none."""
    if user_id is None:
        return False
    return await get_spicedb_client().check_permission(
        resource_type="board",
        resource_id=board_resource_id(session_id),
        permission=permission,
        subject_type="user",
        subject_id=user_id,
    )


async def require_board_permission(user_id: str, session_id: str, permission: str) -> None:
    """Raise 403 unless the user holds `board.<permission>`."""
    if not await can_on_board(user_id, session_id, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: the board permission '{permission}' is required",
        )


async def require_campaign_run_session(user_id: str, campaign_id: str) -> None:
    """Raise 403 unless the user holds `campaign.run_session` on the campaign."""
    allowed = await get_spicedb_client().check_permission(
        resource_type="campaign",
        resource_id=campaign_id,
        permission="run_session",
        subject_type="user",
        subject_id=user_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: run_session on the campaign is required to create a board",
        )


async def bind_board_to_campaign(session_id: str, campaign_id: str) -> None:
    """Write `board:<id>#campaign@campaign:<cid>`. No error is suppressed."""
    await get_spicedb_client().write_relationship(
        resource_type="board",
        resource_id=board_resource_id(session_id),
        relation="campaign",
        subject_type="campaign",
        subject_id=campaign_id,
    )
