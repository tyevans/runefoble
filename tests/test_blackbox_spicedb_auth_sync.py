"""Blackbox TDD frontdoor tests for Zitadel to SpiceDB authorization synchronization."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.spicedb import MockSpiceDBClient, Relationship
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events.events import CharacterCreated, ParticipantJoined, SessionCreated

client = TestClient(app)


@pytest.mark.asyncio
async def test_token_roles_grant_no_campaign_relations(signing_issuer) -> None:
    """A verified token that carries owner and GM roles grants no campaign relation (TASK-0534)."""
    campaign_id = f"camp-{uuid4().hex[:6]}"
    user_id = f"user-{uuid4().hex[:6]}"
    token = signing_issuer.mint(user_id, extra_claims={"roles": ["owner", "dungeon_master"]})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/sessions/{campaign_id}", headers=headers)
    assert res.status_code == 403

    spicedb = get_spicedb_client()
    for permission in ("manage", "run_session", "play", "view"):
        assert not await spicedb.check_permission(
            "campaign", campaign_id, permission, "user", user_id
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
            "type": "runefoble.events.board.token_placed",
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
