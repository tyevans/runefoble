"""Campaign-role gate for the session link on `game_session` (TASK-0856, ADR-0015 (a)).

The `session` object type is removed. `game_session#campaign` is the one campaign link. The
`observe` rule must still grant every campaign role that the old `session` rule granted:
view (spectator, player, DM, GM, owner) and nothing for an outsider.
"""

from __future__ import annotations

import pytest
from runefoble_auth.mock import MockSpiceDBClient

CAMPAIGN = "camp-equiv"
SESSION = "sess-equiv"

ROLE_HOLDERS = {
    "owner": "u-owner",
    "dungeon_master": "u-dm",
    "game_master": "u-gm",
    "player": "u-player",
    "spectator": "u-spectator",
}
OUTSIDER = "u-outsider"


async def _seed(client: MockSpiceDBClient) -> None:
    for relation, user in ROLE_HOLDERS.items():
        await client.write_relationship(
            resource_type="campaign",
            resource_id=CAMPAIGN,
            relation=relation,
            subject_type="user",
            subject_id=user,
        )
    await client.write_relationship(
        resource_type="game_session",
        resource_id=SESSION,
        relation="campaign",
        subject_type="campaign",
        subject_id=CAMPAIGN,
    )


@pytest.mark.asyncio
async def test_observe_rule_keeps_the_campaign_roles_that_session_grants() -> None:
    client = MockSpiceDBClient()
    await _seed(client)
    expected = {
        "owner": True,
        "dungeon_master": True,
        "game_master": True,
        "player": True,
        "spectator": True,
    }
    for role, user in ROLE_HOLDERS.items():
        granted = await client.check_permission(
            resource_type="game_session",
            resource_id=SESSION,
            permission="observe",
            subject_type="user",
            subject_id=user,
        )
        assert granted is expected[role], role
    assert not await client.check_permission(
        resource_type="game_session",
        resource_id=SESSION,
        permission="observe",
        subject_type="user",
        subject_id=OUTSIDER,
    )
