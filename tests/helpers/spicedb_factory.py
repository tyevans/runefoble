"""Test seam over the single shared SpiceDB client factory.

Every service and library caller reads `runefoble_auth.factory.get_spicedb_client()`. A test
swaps that one client with the public seam `set_spicedb_client` (TASK-0818). The swap replaces
the SpiceDB process boundary only. It never patches a caller module, so every caller sees the
same client.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from runefoble_auth.factory import get_spicedb_client, set_spicedb_client

from tests.helpers.module_state import restored_seam


def shared_spicedb_client(client: Any) -> Any:
    """Return a context manager that makes `client` the factory client inside the block.

    The previous client returns when the block exits. Use it as `with shared_spicedb_client(db):`.
    """
    return restored_seam(get_spicedb_client, set_spicedb_client, client, replace=True)


async def bind_session_to_campaign(session_id: str, campaign_id: str) -> None:
    """Write `game_session:<session_id>#campaign@campaign:<campaign_id>` on the shared client.

    `session.control` and `session.participate` walk this relation to reach the campaign
    role. The tuple uses the schema relation name. It is the setup for Watcher tests that
    start from a session id without a game_session frontdoor.
    """
    await get_spicedb_client().write_relationship(
        resource_type="game_session",
        resource_id=str(session_id),
        relation="campaign",
        subject_type="campaign",
        subject_id=str(campaign_id),
    )


async def make_table_runner(user_id: str, session_id: str, campaign_id: str) -> None:
    """Make `user_id` the DM of `session_id` through schema relations only.

    Writes `campaign:<campaign_id>#dungeon_master@user:<user_id>` and binds the session
    to the campaign. `run_session` and `control` then grant the DM permissions.
    """
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=str(campaign_id),
        relation="dungeon_master",
        subject_type="user",
        subject_id=user_id,
    )
    await bind_session_to_campaign(session_id, campaign_id)


async def bind_character_owner(user_id: str, character_id: str) -> None:
    """Write `character:<character_id>#owner@user:<user_id>` on the shared client.

    `character.edit` grants the owner. A player who speaks for this character passes the
    speaker check. The tuple uses the schema relation name.
    """
    await get_spicedb_client().write_relationship(
        resource_type="character",
        resource_id=str(character_id),
        relation="owner",
        subject_type="user",
        subject_id=user_id,
    )


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
    """Link `session_id` to its campaign, make `dm` the DM, and add `players` as players.

    No public frontdoor creates a voice-only session. `campaign#dungeon_master` gives
    `session.control` and `session.participate`. `campaign#player` gives
    `session.participate` only. Grant only what a test needs. A denial test must not grant it.
    """
    campaign_id = campaign_for(session_id)
    await make_table_runner(dm, session_id, campaign_id)
    for player in players:
        await get_spicedb_client().write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id=player,
        )
