"""Session participation policy: a session participant, or a player of the session's campaign."""

from __future__ import annotations

from fastapi import HTTPException
from game_session.aggregate import GameSessionAggregate
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.identifiers import opaque_aggregate_id


async def check_session_participation(
    session_repo: AggregateRepository[GameSessionAggregate], session_id: str, user_id: str
) -> None:
    """Allow the user to participate in the session, or raise 403.

    A session with no event history has no campaign link, so no campaign grant applies.
    A store error propagates to the caller and maps to 503.
    """
    spicedb = get_spicedb_client()
    has_perm = await check_subject(spicedb, "game_session", str(session_id), "participate", user_id)
    if not has_perm:
        sess = await load_if_exists(
            session_repo, opaque_aggregate_id(session_id, field="session_id")
        )
        if sess is not None and sess.state.campaign_id:
            has_perm = await check_subject(
                spicedb, "campaign", str(sess.state.campaign_id), "play", user_id
            )
    if not has_perm:
        raise HTTPException(status_code=403, detail="Player or DM permission required")


__all__ = ["check_session_participation"]
