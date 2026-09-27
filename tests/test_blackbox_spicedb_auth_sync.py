"""Blackbox TDD frontdoor tests for Zitadel to SpiceDB authorization synchronization."""

from uuid import uuid4

import pytest
from runefoble_auth.spicedb import MockSpiceDBClient, Relationship
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_auth.zitadel import AuthenticatedUser
from runefoble_events import CharacterCreated, ParticipantJoined, SessionCreated


@pytest.mark.asyncio
async def test_auth_sync_user_claims_and_permissions() -> None:
    """Verify syncing user claims creates valid tuples and enables permissions."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    campaign_id = f"camp-{uuid4().hex[:6]}"
    user_id = f"user-{uuid4().hex[:6]}"

    user = AuthenticatedUser(user_id=user_id, username="Bob", roles=["player"])
    synced = await service.sync_user_claims(user, campaign_id=campaign_id)
    assert len(synced) > 0

    assert await spicedb.check_permission("campaign", campaign_id, "play", "user", user_id)
    assert await spicedb.check_permission("campaign", campaign_id, "view", "user", user_id)
    assert not await spicedb.check_permission(
        "campaign", campaign_id, "run_session", "user", user_id
    )


@pytest.mark.asyncio
async def test_auth_sync_membership_lifecycle() -> None:
    """Verify granting and revoking campaign memberships."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    campaign_id = f"camp-{uuid4().hex[:6]}"
    dm_id = f"dm-{uuid4().hex[:6]}"

    # Grant DM role
    await service.sync_membership(campaign_id, dm_id, role="dungeon_master", action="grant")
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)

    # Revoke DM role
    await service.sync_membership(campaign_id, dm_id, role="dungeon_master", action="revoke")
    assert not await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)


@pytest.mark.asyncio
async def test_auth_sync_domain_event_orchestration() -> None:
    """Verify domain events emit appropriate authorization tuples."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)

    camp_id = f"camp-{uuid4().hex[:6]}"
    dm_id = f"dm-{uuid4().hex[:6]}"
    player_id = f"player-{uuid4().hex[:6]}"
    sess_id = f"sess-{uuid4().hex[:6]}"
    char_id = uuid4()
    token_id = f"tok-{uuid4().hex[:6]}"

    # 1. Session created
    await service.handle_domain_event(
        SessionCreated(aggregate_id=uuid4(), campaign_id=camp_id, session_id=sess_id, dm_id=dm_id)
    )
    assert await spicedb.check_permission("session", sess_id, "control", "user", dm_id)

    # 2. Participant joined
    await service.handle_domain_event(
        ParticipantJoined(
            aggregate_id=uuid4(),
            campaign_id=camp_id,
            session_id=sess_id,
            user_id=player_id,
            role="player",
        )
    )
    assert await spicedb.check_permission("session", sess_id, "participate", "user", player_id)

    # 3. Character created
    await service.handle_domain_event(
        CharacterCreated(
            aggregate_id=char_id,
            player_id=player_id,
            campaign_id=camp_id,
            name="Kyra",
            character_class="Cleric",
            max_hp=18,
            current_hp=18,
        )
    )
    assert await spicedb.check_permission("character", str(char_id), "edit", "user", player_id)
    assert await spicedb.check_permission("character", str(char_id), "edit", "user", dm_id)

    # 4. Token placed
    await service.handle_domain_event(
        {
            "type": "TokenPlaced",
            "data": {"token_id": token_id, "character_id": str(char_id), "campaign_id": camp_id},
        }
    )
    assert await spicedb.check_permission("board_token", token_id, "move", "user", player_id)
    assert await spicedb.check_permission("board_token", token_id, "move", "user", dm_id)


@pytest.mark.asyncio
async def test_auth_sync_batch_reconcile() -> None:
    """Verify batch writes and reconciliation."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)

    rels = [
        Relationship("campaign", "c_sync", "player", "user", "u1"),
        Relationship("campaign", "c_sync", "spectator", "user", "u2"),
    ]
    await service.batch_write_relationships(rels)
    result = await service.reconcile_relationships(rels)
    assert result["reconciled"] is True
    assert result["added_count"] == 0
