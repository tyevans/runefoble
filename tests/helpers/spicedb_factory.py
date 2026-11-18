"""Test seam over the single shared SpiceDB client factory.

Every gateway and library caller reads `runefoble_auth.factory.get_spicedb_client()`. A test
swaps the factory cache with this helper. The swap replaces the SpiceDB process boundary only.
It never patches a caller module, so every caller sees the same client.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from unittest.mock import patch

import runefoble_auth.factory as spicedb_factory


def shared_spicedb_client(client: Any) -> Any:
    """Return a patch that makes `client` the factory client until the patch stops.

    Use it as a context manager (`with shared_spicedb_client(db): ...`) or call
    `start()` and `stop()` in a fixture.
    """
    return patch.object(spicedb_factory, "_client", client)


async def bind_session_to_campaign(session_id: str, campaign_id: str) -> None:
    """Write `session:<session_id>#campaign@campaign:<campaign_id>` on the shared client.

    `session.control` and `session.participate` walk this relation to reach the campaign
    role. The tuple uses the schema relation name. It is the setup for Watcher tests that
    start from a session id without a game_session frontdoor.
    """
    from runefoble_auth.factory import get_spicedb_client

    await get_spicedb_client().write_relationship(
        resource_type="session",
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
    from runefoble_auth.factory import get_spicedb_client

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
    from runefoble_auth.factory import get_spicedb_client

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
    from runefoble_auth.factory import get_spicedb_client

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
