"""Schema tuples that let a voice test speak and moderate in a session (TASK-0558).

No public frontdoor creates a voice-only session. These helpers write relationship
tuples through the shared SpiceDB seam, and they use schema names only:

- `session#campaign` links the session to its campaign.
- `campaign#dungeon_master` gives `session.control` and `session.participate`.
- `campaign#player` gives `session.participate` only.

Grant only the sessions and speakers a test needs. A denial test must not grant them.
"""

from __future__ import annotations

from collections.abc import Iterable

from runefoble_auth.factory import get_spicedb_client

VOICE_DM = "user-dm"


def campaign_for(session_id: str) -> str:
    """Return the campaign id that a voice test session belongs to."""
    return f"camp-{session_id}"


async def grant_voice_session(
    session_id: str,
    *,
    dm: str = VOICE_DM,
    players: Iterable[str] = (),
) -> None:
    """Link `session_id` to its campaign, make `dm` the DM, and add `players` as players."""
    spicedb = get_spicedb_client()
    campaign_id = campaign_for(session_id)
    await spicedb.write_relationship("session", session_id, "campaign", "campaign", campaign_id)
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm)
    for player in players:
        await spicedb.write_relationship("campaign", campaign_id, "player", "user", player)


__all__ = ["VOICE_DM", "campaign_for", "grant_voice_session"]
