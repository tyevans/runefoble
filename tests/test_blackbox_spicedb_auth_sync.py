"""Blackbox TDD frontdoor tests for Zitadel to SpiceDB authorization synchronization."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.mock import MockSpiceDBClient, Relationship
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events.events import CharacterCreated, SessionCreated

from tests.helpers.sync_verifier import sync_test_verifier


@pytest.mark.asyncio
async def test_token_roles_grant_no_campaign_relations(
    trusted_ws_issuer, game_session_upstream
) -> None:
    """A verified token that carries owner and GM roles grants no campaign relation (TASK-0534)."""
    campaign_id = f"camp-{uuid4().hex[:6]}"
    user_id = f"user-{uuid4().hex[:6]}"
    token = trusted_ws_issuer.mint(user_id, extra_claims={"roles": ["owner", "dungeon_master"]})
    headers = {"Authorization": f"Bearer {token}"}

    # game_session checks `session.observe`; the token roles grant nothing (TASK-0845 rule).
    with TestClient(app) as client:
        res = client.get(f"/api/v1/sessions/{uuid4()}", headers=headers)
    assert res.status_code == 403, res.text

    spicedb = get_spicedb_client()
    for permission in ("manage", "run_session", "play", "view"):
        assert not await spicedb.check_permission(
            "campaign", campaign_id, permission, "user", user_id
        )


@pytest.mark.asyncio
async def test_domain_events_carry_role_names_into_no_campaign_relation() -> None:
    """A role named in a domain event writes no campaign relation (ADR-0015 (d), TASK-0855).

    The DM of a new session and a player who joins as `owner` both get no campaign grant.
    Memberships come only from the campaign roles and join routes.
    """
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb, zitadel_auth=sync_test_verifier())
    camp_id = f"camp-{uuid4().hex[:6]}"
    dm_id = f"dm-{uuid4().hex[:6]}"
    joiner_id = f"joiner-{uuid4().hex[:6]}"

    await service.handle_domain_event(
        SessionCreated(
            aggregate_id=uuid4(), campaign_id=camp_id, session_id=f"sess-{camp_id}", dm_id=dm_id
        )
    )
    await service.handle_domain_event(
        {
            "type": "runefoble.events.session.player_joined_session",
            "data": {"campaign_id": camp_id, "user_id": joiner_id, "role": "owner"},
        }
    )

    for permission in ("manage", "run_session", "play", "view"):
        assert not await spicedb.check_permission("campaign", camp_id, permission, "user", dm_id)
        assert not await spicedb.check_permission(
            "campaign", camp_id, permission, "user", joiner_id
        )


@pytest.mark.asyncio
async def test_auth_sync_domain_event_orchestration() -> None:
    """Verify domain events emit appropriate authorization tuples."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb, zitadel_auth=sync_test_verifier())

    camp_id = f"camp-{uuid4().hex[:6]}"
    player_id = f"player-{uuid4().hex[:6]}"
    char_id = uuid4()
    token_id = f"tok-{uuid4().hex[:6]}"

    # 1. Character created
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

    # 2. Token placed
    await service.handle_domain_event(
        {
            "type": "runefoble.events.board.token_placed",
            "data": {"token_id": token_id, "character_id": str(char_id), "campaign_id": camp_id},
        }
    )
    assert await spicedb.check_permission("board_token", token_id, "move", "user", player_id)


@pytest.mark.asyncio
async def test_auth_sync_batch_reconcile() -> None:
    """Verify batch writes and reconciliation."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb, zitadel_auth=sync_test_verifier())

    rels = [
        Relationship("campaign", "c_sync", "player", "user", "u1"),
        Relationship("campaign", "c_sync", "spectator", "user", "u2"),
    ]
    await service.batch_write_relationships(rels)
    result = await service.reconcile_relationships(rels)
    assert result["reconciled"] is True
    assert result["added_count"] == 0
