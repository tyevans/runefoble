"""Blackbox TDD frontdoor tests for SpiceDBClient operations and fallbacks."""

from uuid import uuid4

import pytest
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_spicedb_client_mock_crud() -> None:
    """Verify MockSpiceDBClient in-memory evaluation."""
    client = MockSpiceDBClient()
    campaign_id = f"camp-{uuid4().hex[:6]}"
    user_id = f"user-{uuid4().hex[:6]}"

    # Touch relationship
    await client.touch_relationship("campaign", campaign_id, "dungeon_master", "user", user_id)

    # Check permission
    assert await client.check_permission("campaign", campaign_id, "run_session", "user", user_id)
    assert await client.check_permission("campaign", campaign_id, "view", "user", user_id)
    assert not await client.check_permission(
        "campaign", campaign_id, "run_session", "user", "intruder"
    )

    # Read relationships with filter
    rels = await client.read_relationships(resource_type="campaign", resource_id=campaign_id)
    assert len(rels) == 1
    assert rels[0].relation == "dungeon_master"

    # Delete relationship
    await client.delete_relationship("campaign", campaign_id, "dungeon_master", "user", user_id)
    assert not await client.check_permission(
        "campaign", campaign_id, "run_session", "user", user_id
    )


@pytest.mark.asyncio
async def test_spicedb_multi_entity_authorization() -> None:
    """Verify authorization graphs across character, board_token, and shared_world."""
    client = MockSpiceDBClient()
    camp_id = f"camp-{uuid4().hex[:6]}"
    dm_id = f"dm-{uuid4().hex[:6]}"
    player_id = f"player-{uuid4().hex[:6]}"
    char_id = f"char-{uuid4().hex[:6]}"
    token_id = f"tok-{uuid4().hex[:6]}"
    world_id = f"world-{uuid4().hex[:6]}"
    contract_id = f"contract-{uuid4().hex[:6]}"

    # Campaign memberships
    await client.write_relationship("campaign", camp_id, "dungeon_master", "user", dm_id)
    await client.write_relationship("campaign", camp_id, "player", "user", player_id)

    # Character linked to campaign & owner
    await client.write_relationship("character", char_id, "campaign", "campaign", camp_id)
    await client.write_relationship("character", char_id, "owner", "user", player_id)

    # Board token linked to character & campaign
    await client.write_relationship("board_token", token_id, "character", "character", char_id)
    await client.write_relationship("board_token", token_id, "campaign", "campaign", camp_id)

    # Player and DM can move token
    assert await client.check_permission("board_token", token_id, "move", "user", player_id)
    assert await client.check_permission("board_token", token_id, "move", "user", dm_id)
    assert not await client.check_permission("board_token", token_id, "move", "user", "stranger")

    # Shared world & caravan contracts
    await client.write_relationship("shared_world", world_id, "participant", "user", player_id)
    await client.write_relationship(
        "caravan_contract", contract_id, "shared_world", "shared_world", world_id
    )
    await client.write_relationship("caravan_contract", contract_id, "poster", "user", player_id)

    assert await client.check_permission(
        "caravan_contract", contract_id, "manage", "user", player_id
    )
    assert await client.check_permission("caravan_contract", contract_id, "view", "user", player_id)
