"""Session participation policy: a session participant, or a player of the session's campaign."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from game_session.dependencies import get_spicedb_client
from game_session.dependencies import repo as session_repo
from runefoble_platform.aggregate_loading import load_if_exists


async def check_session_participation(session_id: str, user_id: str) -> None:
    """Allow the user to participate in the session, or raise 403.

    A session with no event history has no campaign link, so no campaign grant applies.
    A store error propagates to the caller and maps to 503.
    """
    spicedb = get_spicedb_client()
    has_perm = await spicedb.check_permission(
        "session", str(session_id), "participate", "user", user_id
    )
    if not has_perm:
        sess = await load_if_exists(
            session_repo, UUID(session_id) if len(session_id) == 36 else session_id
        )
        if sess is not None and sess.state.campaign_id:
            has_perm = await spicedb.check_permission(
                "campaign", str(sess.state.campaign_id), "play", "user", user_id
            )
    if not has_perm:
        raise HTTPException(status_code=403, detail="Player or DM permission required")


__all__ = ["check_session_participation"]
