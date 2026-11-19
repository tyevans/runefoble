"""Stream names, the service logger, and the SpiceDB permission checks of The Watcher.

The engines, repositories, and the event bus are in the app container (`container.py`).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from runefoble_auth.contract import permission_for_action
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject

logger = logging.getLogger("runefoble.the_watcher")

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_BOARD = "runefoble.events.board"
STREAM_WORLD = "runefoble.events.world"


async def check_action_permission(
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
) -> bool:
    """Return True when the user holds the schema permission behind `action`.

    `action` is a key of `ACTION_PERMISSIONS`. The type of the action must match
    `resource_type`. SpiceDB errors propagate (fail closed): only a definitive denial
    returns False.
    """
    action_type, permission = permission_for_action(action)
    if action_type != resource_type:
        raise ValueError(f"Action '{action}' checks '{action_type}', not '{resource_type}'")
    return await check_subject(
        get_spicedb_client(), resource_type, str(resource_id), permission, user_id
    )


async def require_campaign_permission(user_id: str, campaign_id: str | None, action: str) -> None:
    """Raise 403 unless the user holds the campaign permission behind `action`.

    A missing campaign id is a denial. The check never passes by default.
    """
    if not campaign_id or not await check_action_permission(
        user_id, "campaign", campaign_id, action
    ):
        raise HTTPException(status_code=403, detail=_denied(action, "campaign", campaign_id))


async def require_character_permission(user_id: str, character_id: str | None, action: str) -> None:
    """Raise 403 unless the user holds the character permission behind `action`."""
    if not character_id or not await check_action_permission(
        user_id, "character", character_id, action
    ):
        raise HTTPException(status_code=403, detail=_denied(action, "character", character_id))


async def require_speaker(user_id: str, speaker_id: str) -> None:
    """Allow a player to speak as themselves, or for a character they can edit.

    A speaker that is neither the caller nor an editable character gets 403.
    """
    if speaker_id == user_id:
        return
    await require_character_permission(user_id, speaker_id, "character.edit")


async def require_session_permission(user_id: str, session_id: str | None, action: str) -> None:
    """Raise 403 unless the user holds the session permission behind `action`."""
    if not session_id or not await check_action_permission(
        user_id, "game_session", session_id, action
    ):
        raise HTTPException(status_code=403, detail=_denied(action, "game_session", session_id))


async def require_dm(
    user_id: str, campaign_id: str | None = None, session_id: str | None = None
) -> None:
    """Raise 403 unless `check_dm_authorization` grants the table-run permission for the scope."""
    if not await check_dm_authorization(user_id, campaign_id=campaign_id, session_id=session_id):
        action = "session.control" if session_id else "campaign.run_session"
        resource_type, resource_id = (
            ("game_session", session_id) if session_id else ("campaign", campaign_id)
        )
        raise HTTPException(status_code=403, detail=_denied(action, resource_type, resource_id))


def _denied(action: str, resource_type: str, resource_id: str | None) -> str:
    return (
        f"Forbidden: Zanzibar authorization denied. Action '{action}' requires "
        f"permission on {resource_type} '{resource_id or 'unknown'}'."
    )


async def check_dm_authorization(
    user_id: str,
    campaign_id: str | None = None,
    session_id: str | None = None,
) -> bool:
    """Return True when the user may run the table (DM, GM, or owner).

    A session scope is decided by `session.control` only. Mixing a campaign id from one
    campaign with a session from another must not pass. Without a session the campaign
    permission `campaign.run_session` decides.
    """
    if session_id:
        return await check_action_permission(user_id, "game_session", session_id, "session.control")
    if campaign_id:
        return await check_action_permission(
            user_id, "campaign", campaign_id, "campaign.run_session"
        )
    return False
