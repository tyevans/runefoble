"""Board permission checks against the SpiceDB `board` schema (ADR-0001).

Every check names a schema permission of `definition board` in `runefoble.zed`. No role name
appears here. `board.campaign` links a board to its campaign. Creation writes that tuple.
A SpiceDB failure raises `AuthzError`. The app maps it to 503 or 500 and never to a denial.
"""

from __future__ import annotations

import re

from board_state.dependencies import to_board_uuid
from fastapi import HTTPException, status
from runefoble_auth.factory import get_spicedb_client

MANAGE_TRAPS = "manage_traps"
VIEW_SECRET_LAYER = "view_secret_layer"
SWITCH_MAP = "switch_map"
VIEW = "view"
PLAY = "play"
TOKEN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-=+|/]{1,128}$")


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


async def record_forged_asset_owner(asset_id: str, creator_id: str, session_id: str) -> None:
    """Write `forged_asset` creator and, when the board has one, campaign tuples (TASK-0785).

    An imported map image becomes an authorized asset, as a forged asset does. No error is
    suppressed. A failed write raises AuthzError, and the caller removes the stored object.
    """
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="forged_asset",
        resource_id=asset_id,
        relation="creator",
        subject_type="user",
        subject_id=creator_id,
    )
    campaign_id = await board_campaign_id(session_id)
    if campaign_id:
        await spicedb.write_relationship(
            resource_type="forged_asset",
            resource_id=asset_id,
            relation="campaign",
            subject_type="campaign",
            subject_id=campaign_id,
        )


async def board_campaign_id(session_id: str) -> str | None:
    """Return the campaign that owns the board, or None when the board tuple is missing."""
    found = await get_spicedb_client().read_relationships(
        resource_type="board", resource_id=board_resource_id(session_id), relation="campaign"
    )
    return found[0].subject_id if found else None


async def can_on_campaign(user_id: str | None, session_id: str, permission: str) -> bool:
    """Return whether the user holds `campaign.<permission>` on the campaign of the board."""
    if user_id is None:
        return False
    campaign_id = await board_campaign_id(session_id)
    if campaign_id is None:
        return False
    return await get_spicedb_client().check_permission(
        resource_type="campaign",
        resource_id=campaign_id,
        permission=permission,
        subject_type="user",
        subject_id=user_id,
    )


async def can_move_token(user_id: str | None, session_id: str, token_id: str) -> bool:
    """Return whether the user holds `board_token.move` on the token, or runs the board."""
    if user_id is None:
        return False
    if await get_spicedb_client().check_permission(
        resource_type="board_token",
        resource_id=token_id,
        permission="move",
        subject_type="user",
        subject_id=user_id,
    ):
        return True
    return await can_on_board(user_id, session_id, MANAGE_TRAPS)


async def require_campaign_permission(user_id: str, session_id: str, permission: str) -> None:
    """Raise 403 unless the user holds `campaign.<permission>` on the board campaign."""
    if not await can_on_campaign(user_id, session_id, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: the campaign permission '{permission}' is required",
        )


async def require_token_move(user_id: str, session_id: str, token_id: str) -> None:
    """Raise 403 unless the user holds `board_token.move` on the token or runs the board."""
    if not await can_move_token(user_id, session_id, token_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: moving this token requires its character or a board manager",
        )


async def bind_token(
    session_id: str, token_id: str, character_id: str | None, user_id: str
) -> None:
    """Authorize a placement, then write the `board_token` tuples. Raise 403 or 409 on refusal.

    A character token needs `character.edit` and `campaign.play`. Any other token needs
    `board.manage_traps`. An id that already belongs to another campaign or character is refused.
    """
    if not TOKEN_ID_PATTERN.fullmatch(token_id):
        raise HTTPException(status_code=400, detail="token_id has characters that are not allowed")
    client = get_spicedb_client()
    if character_id is None:
        await require_board_permission(user_id, session_id, MANAGE_TRAPS)
    else:
        await require_campaign_permission(user_id, session_id, PLAY)
        if not await client.check_permission(
            resource_type="character",
            resource_id=character_id,
            permission="edit",
            subject_type="user",
            subject_id=user_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: placing a character token requires character.edit",
            )
    campaign_id = await board_campaign_id(session_id)
    if campaign_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Board has no campaign")
    held = await client.read_relationships(resource_type="board_token", resource_id=token_id)
    wanted = {("campaign", campaign_id)} | (
        {("character", character_id)} if character_id else set()
    )
    if any((r.relation, r.subject_id) not in wanted for r in held):
        raise HTTPException(status_code=409, detail="token_id already belongs to another token")
    for relation, subject_type, subject_id in [
        ("campaign", "campaign", campaign_id),
        *([("character", "character", character_id)] if character_id else []),
    ]:
        await client.touch_relationship(
            resource_type="board_token",
            resource_id=token_id,
            relation=relation,
            subject_type=subject_type,
            subject_id=subject_id,
        )


async def unbind_token(token_id: str) -> None:
    """Delete every `board_token` tuple of a removed token."""
    client = get_spicedb_client()
    for held in await client.read_relationships(resource_type="board_token", resource_id=token_id):
        await client.delete_relationship(
            resource_type="board_token",
            resource_id=token_id,
            relation=held.relation,
            subject_type=held.subject_type,
            subject_id=held.subject_id,
        )
