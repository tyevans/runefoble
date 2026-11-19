"""Tests for SpiceDB client operations and Zanzibar relationship synchronization."""

from uuid import uuid4

import pytest
from runefoble_auth.mock import MockSpiceDBClient, Relationship
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.sync import SyncResult, ZitadelSpiceDBSyncService
from runefoble_auth.sync_events import handle_domain_event
from runefoble_auth.sync_tuples import (
    CAMPAIGN_ROLE_RELATIONS,
    format_tuple,
    normalize_campaign_role,
)
from runefoble_events.events import CharacterCreated, SessionCreated
from runefoble_platform.event_fields import event_type_of


@pytest.mark.asyncio
async def test_spicedb_client_crud_and_permissions(
    live_spicedb_endpoint: str | None = None,
) -> None:
    """Verify SpiceDBClient relationship writing and permission evaluation."""
    if live_spicedb_endpoint:
        client = SpiceDBClient(endpoint=live_spicedb_endpoint, token="test_token")
        from runefoble_auth.bootstrap_schema import bootstrap_schema

        await bootstrap_schema(client=client)
    else:
        client = MockSpiceDBClient()
    campaign_id = f"camp-{uuid4().hex[:6]}"
    user_id = f"user-{uuid4().hex[:6]}"

    await client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=user_id,
    )

    assert await client.check_permission("campaign", campaign_id, "run_session", "user", user_id)
    assert not await client.check_permission(
        "campaign", campaign_id, "run_session", "user", "other_user"
    )

    await client.delete_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=user_id,
    )
    assert not await client.check_permission(
        "campaign", campaign_id, "run_session", "user", user_id
    )


def test_sync_tuples_helpers_and_models() -> None:
    """Verify SyncResult, tuple formatting, and role normalization."""
    result = SyncResult(status="success", synced_tuples=["campaign:c1#game_master@user:u1"])
    assert result.status == "success"
    assert len(result.synced_tuples) == 1

    formatted = format_tuple("campaign", "c1", "player", "user", "u2")
    assert formatted == "campaign:c1#player@user:u2"

    assert normalize_campaign_role("gm") == ["game_master"]
    assert normalize_campaign_role("dm") == ["game_master"]
    assert normalize_campaign_role("player") == ["player"]
    assert normalize_campaign_role("custom_role") == ["custom_role"]
    assert "spectator" in CAMPAIGN_ROLE_RELATIONS


@pytest.mark.asyncio
async def test_handle_domain_event_dispatch() -> None:
    """Verify handle_domain_event routes domain event instances and CloudEvent dicts."""
    spicedb = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)

    camp_id = f"camp-evt-{uuid4().hex[:6]}"
    dm_id = f"dm-{uuid4().hex[:6]}"
    sess_id = f"sess-{uuid4().hex[:6]}"

    # 1. Pydantic SessionCreated
    evt_session = SessionCreated(
        aggregate_id=uuid4(),
        campaign_id=camp_id,
        session_id=sess_id,
        dm_id=dm_id,
    )
    synced_session = await service.handle_domain_event(evt_session)
    assert any("campaign:" in t and "#game_master@" in t for t in synced_session)

    # 3. Pydantic CharacterCreated
    user_id = f"player-{uuid4().hex[:6]}"
    char_id = uuid4()
    evt_char = CharacterCreated(
        aggregate_id=char_id,
        player_id=user_id,
        campaign_id=camp_id,
        name="Valeros",
        character_class="Fighter",
        max_hp=20,
        current_hp=20,
    )
    synced_char = await service.handle_domain_event(evt_char)
    assert any(f"character:{char_id}#owner@user:{user_id}" in t for t in synced_char)

    # 4. TokenPlaced CloudEvent
    tok_id = f"tok-{uuid4().hex[:6]}"
    evt_tok = {
        "type": "runefoble.events.board.token_placed",
        "data": {
            "token_id": tok_id,
            "character_id": str(char_id),
            "campaign_id": camp_id,
        },
    }
    synced_tok = await service.handle_domain_event(evt_tok)
    assert any(f"board_token:{tok_id}#character@character:{char_id}" in t for t in synced_tok)

    # 5. CloudEvent dict payload
    dict_event = {
        "type": "runefoble.events.session.created",
        "data": {
            "campaign_id": f"camp-dict-{uuid4().hex[:6]}",
            "dm_id": "dict_dm",
            "session_id": "dict_sess",
        },
    }
    synced_dict = await handle_domain_event(service, dict_event)
    assert len(synced_dict) > 0

    # 6. Unknown event type returns empty list
    assert await service.handle_domain_event({"type": "UnknownEvent"}) == []
    assert event_type_of({"type": "org.runefoble.CustomEvent"}) == "org.runefoble.CustomEvent"


@pytest.mark.asyncio
async def test_reconcile_and_batch_relationships() -> None:
    """Verify batch_write_relationships and reconcile_relationships."""
    client = MockSpiceDBClient()
    service = ZitadelSpiceDBSyncService(spicedb_client=client)

    rels = [
        Relationship("campaign", "c1", "player", "user", "u1"),
        Relationship("campaign", "c1", "game_master", "user", "u2"),
    ]
    synced = await service.batch_write_relationships(rels)
    assert len(synced) == 2

    # Reconcile when tuples already exist
    reconciled = await service.reconcile_relationships(rels)
    assert reconciled["reconciled"] is True
    assert reconciled["added_count"] == 0

    # Reconcile adding new tuple
    new_rels = rels + [Relationship("campaign", "c1", "spectator", "user", "u3")]
    reconciled_new = await service.reconcile_relationships(new_rels)
    assert reconciled_new["added_count"] == 1
