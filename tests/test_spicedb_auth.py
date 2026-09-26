import pytest
from runefoble_auth.spicedb import SpiceDBClient


@pytest.mark.asyncio
async def test_spicedb_zanzibar_permissions():
    client = SpiceDBClient()

    # User Alice is DM for campaign 'camp_1'
    await client.write_relationship(
        resource_type="campaign",
        resource_id="camp_1",
        relation="dungeon_master",
        subject_type="user",
        subject_id="alice",
    )

    # User Bob is player
    await client.write_relationship(
        resource_type="campaign",
        resource_id="camp_1",
        relation="player",
        subject_type="user",
        subject_id="bob",
    )

    # Alice can run_session and play
    assert await client.check_permission("campaign", "camp_1", "run_session", "user", "alice")
    assert await client.check_permission("campaign", "camp_1", "play", "user", "alice")

    # Bob can play and view, but not run_session
    assert await client.check_permission("campaign", "camp_1", "play", "user", "bob")
    assert await client.check_permission("campaign", "camp_1", "view", "user", "bob")
    assert not await client.check_permission("campaign", "camp_1", "run_session", "user", "bob")

    # Charlie is an outsider with no permissions
    assert not await client.check_permission("campaign", "camp_1", "view", "user", "charlie")
