"""Test seam over the single shared SpiceDB client factory.

Every gateway and library caller reads `runefoble_auth.factory.get_spicedb_client()`. A test
swaps the factory cache with this helper. The swap replaces the SpiceDB process boundary only.
It never patches a caller module, so every caller sees the same client.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

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
