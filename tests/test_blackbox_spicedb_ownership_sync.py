"""Blackbox TDD frontdoor suite for SpiceDB resource ownership and edge cases.

Verifies:
1. Domain event stream synchronization (SessionCreated, ParticipantJoined, CharacterCreated).
2. Character ownership revocation through the character frontdoor.
3. Removed public sync routes return 404. Error handling for malformed event payloads.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.listener import SpiceDBEventListener
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events import CharacterCreated, ParticipantJoined, SessionCreated
from runefoble_platform.bus import EventBus

client = TestClient(app)


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.mark.asyncio
async def test_domain_event_listeners_stream_synchronization() -> None:
    """Publishing domain events automatically provisions SpiceDB Zanzibar relationships."""
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    listener = SpiceDBEventListener(sync_service=sync_service)

    local_bus = EventBus()
    listener.register_bus_handlers(local_bus)

    campaign_id = f"camp-evt-{uuid4().hex[:8]}"
    dm_id = "watcher_dm_99"
    player_id = "barbarian_grog"
    char_id = uuid4()

    # Publish SessionCreated -> DM run_session permission
    session_event = SessionCreated(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        session_id=campaign_id,
        dm_id=dm_id,
        title="Crypt of Shadows",
    )
    await local_bus.publish("SessionCreated", session_event)
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)

    # Publish ParticipantJoined -> player play & view permissions
    participant_event = ParticipantJoined(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        user_id=player_id,
        role="player",
        character_id=char_id,
    )
    await local_bus.publish("ParticipantJoined", participant_event)
    assert await spicedb.check_permission("campaign", campaign_id, "play", "user", player_id)
    assert await spicedb.check_permission("campaign", campaign_id, "view", "user", player_id)

    # Publish CharacterCreated -> character owner edit permission
    char_event = CharacterCreated(
        aggregate_id=char_id,
        name="Grog Strongjaw",
        character_class="Barbarian",
        max_hp=45,
        current_hp=45,
        player_id=player_id,
        campaign_id=campaign_id,
    )
    await local_bus.publish("CharacterCreated", char_event)
    assert await spicedb.check_permission("character", str(char_id), "edit", "user", player_id)


@pytest.mark.asyncio
async def test_character_ownership_revocation_and_removed_sync_routes(signing_issuer) -> None:
    """Deleting an owned character revokes edit rights. The removed sync routes return 404."""
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    listener = SpiceDBEventListener(sync_service=sync_service)

    owner_id = f"user-rev-{uuid4().hex[:6]}"
    owner_headers = _auth(signing_issuer, owner_id)

    # Frontdoor: character creation writes the owner relation
    res = client.post(
        "/api/v1/characters",
        json={"name": "Revocable Rogue", "characterClass": "Rogue", "level": 1, "maxHp": 10},
        headers=owner_headers,
    )
    assert res.status_code == 201, res.text
    char_id = res.json()["id"]
    assert client.get(f"/api/v1/characters/{char_id}", headers=owner_headers).status_code == 200

    # Frontdoor revocation: the owner deletes the character
    res_del = client.delete(f"/api/v1/characters/{char_id}", headers=owner_headers)
    assert res_del.status_code == 200, res_del.text
    assert not await spicedb.check_permission("character", char_id, "edit", "user", owner_id)

    # The public character-ownership sync route is removed (TASK-0543)
    res_removed = client.post(
        "/api/v1/auth/sync/character-ownership",
        json={"character_id": char_id, "user_id": owner_id},
    )
    assert res_removed.status_code == 404

    # Listener edge case: Malformed domain events return empty list without crashing
    assert await listener.on_character_created(object()) == []
    assert await listener.on_session_created(None) == []
    assert await listener.on_participant_joined(object()) == []
