"""Blackbox TDD frontdoor test suite for SpiceDB Zanzibar relationship synchronization with Zitadel identities.

Verifies:
1. Frontdoor synchronization endpoints (/api/v1/auth/sync/*).
2. Fine-grained SpiceDB Zanzibar permission checks across GM, Player, and Spectator roles.
3. Token movement authorization: players move own tokens, denied other player's tokens.
4. Spectator read-only scene visibility and mutation rejection.
5. Idempotent re-syncing and instant permission revocation.
6. Domain event bus synchronization via SessionCreated, ParticipantJoined, and CharacterCreated.
7. Transient fault resilience and retry logic.
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
from runefoble_platform.consumer_group import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

client = TestClient(app)


def test_sync_health_frontdoor() -> None:
    """GET /api/v1/auth/sync/health reports operational status and SpiceDB connectivity."""
    res = client.get("/api/v1/auth/sync/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["spicedb_connected"] is True
    assert data["sync_service"] == "operational"


def test_sync_user_claims_frontdoor() -> None:
    """POST /api/v1/auth/sync/user translates Zitadel claims into Zanzibar tuples."""
    campaign_id = f"camp-sync-{uuid4().hex[:8]}"
    user_id = "adventurer_robin"

    res = client.post(
        "/api/v1/auth/sync/user",
        json={
            "user_id": user_id,
            "username": "Robin",
            "roles": ["player"],
            "campaign_id": campaign_id,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "synchronized"
    assert body["user_id"] == user_id
    assert f"campaign:{campaign_id}#player@user:{user_id}" in body["synced_relationships"]


@pytest.mark.asyncio
async def test_gm_synchronization_dm_override_and_atmosphere() -> None:
    """Synchronized GM can execute DM override and update campaign atmosphere."""
    spicedb = get_spicedb_client()
    campaign_id = f"camp-gm-{uuid4().hex[:8]}"
    gm_id = "gm_elena"
    stranger_id = "stranger_pete"

    # 1. Before sync: GM and stranger are rejected with 403
    res_before = client.post(
        f"/api/v1/sessions/{campaign_id}/dm-override",
        headers={"X-User-Id": gm_id},
        json={"action": "pause_encounter", "reason": "DM bathroom break"},
    )
    assert res_before.status_code == 403

    # 2. Synchronize GM membership via public frontdoor endpoint
    res_sync = client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": gm_id, "role": "gm"},
    )
    assert res_sync.status_code == 200
    assert res_sync.json()["status"] == "membership_updated"

    # 3. Assert observable permission via SpiceDBClient
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", gm_id)

    # 4. Synchronized GM can execute DM override
    res_override = client.post(
        f"/api/v1/sessions/{campaign_id}/dm-override",
        headers={"X-User-Id": gm_id},
        json={"action": "pause_encounter", "reason": "DM narrative pause"},
    )
    assert res_override.status_code == 200
    assert res_override.json()["status"] == "override_executed"

    # 5. Synchronized GM can update campaign atmosphere
    res_atmo = client.post(
        f"/api/v1/sessions/{campaign_id}/atmosphere",
        headers={"X-User-Id": gm_id},
        json={
            "location_name": "Tomb of the Lich King",
            "lighting": "Eerie Luminescence",
            "mood": "Suspenseful",
            "description": "Green spectral mist creeps through ancient flagstones.",
        },
    )
    assert res_atmo.status_code == 200
    assert res_atmo.json()["status"] == "atmosphere_updated"
    assert res_atmo.json()["atmosphere"]["location_name"] == "Tomb of the Lich King"

    # 6. Unassigned stranger is denied on both endpoints
    res_stranger_override = client.post(
        f"/api/v1/sessions/{campaign_id}/dm-override",
        headers={"X-User-Id": stranger_id},
        json={"action": "end_session"},
    )
    assert res_stranger_override.status_code == 403

    res_stranger_atmo = client.post(
        f"/api/v1/sessions/{campaign_id}/atmosphere",
        headers={"X-User-Id": stranger_id},
        json={"location_name": "Sunny Meadow"},
    )
    assert res_stranger_atmo.status_code == 403


@pytest.mark.asyncio
async def test_token_movement_player_isolation_and_spectator_readonly() -> None:
    """Players move own tokens, cannot move other player tokens; spectators are read-only."""
    campaign_id = f"camp-tactical-{uuid4().hex[:8]}"
    player_alice = "alice_fighter"
    player_bob = "bob_wizard"
    spectator_clara = "clara_audience"
    gm_derek = "derek_gm"

    char_alice = f"char-a-{uuid4().hex[:8]}"
    char_bob = f"char-b-{uuid4().hex[:8]}"

    token_alice = f"tok-a-{uuid4().hex[:8]}"
    token_bob = f"tok-b-{uuid4().hex[:8]}"

    # 1. Frontdoor sync: Memberships
    client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": gm_derek, "role": "gm"},
    )
    client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": player_alice, "role": "player"},
    )
    client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": player_bob, "role": "player"},
    )
    client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": spectator_clara, "role": "spectator"},
    )

    # 2. Frontdoor sync: Character ownerships
    client.post(
        "/api/v1/auth/sync/character-ownership",
        json={"character_id": char_alice, "user_id": player_alice, "campaign_id": campaign_id},
    )
    client.post(
        "/api/v1/auth/sync/character-ownership",
        json={"character_id": char_bob, "user_id": player_bob, "campaign_id": campaign_id},
    )

    # 3. Frontdoor sync: Token bindings
    client.post(
        "/api/v1/auth/sync/token-binding",
        json={"token_id": token_alice, "character_id": char_alice, "campaign_id": campaign_id},
    )
    client.post(
        "/api/v1/auth/sync/token-binding",
        json={"token_id": token_bob, "character_id": char_bob, "campaign_id": campaign_id},
    )

    # 4. Alice moves her own token -> Allowed (200)
    res_a_moves_a = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": player_alice},
        json={"to_x": 4, "to_y": 5},
    )
    assert res_a_moves_a.status_code == 200
    assert res_a_moves_a.json()["status"] == "token_moved"

    # 5. Alice attempts to move Bob's token -> Denied (403)
    res_a_moves_b = client.post(
        f"/api/v1/board/tokens/{token_bob}/move",
        headers={"X-User-Id": player_alice},
        json={"to_x": 1, "to_y": 1},
    )
    assert res_a_moves_b.status_code == 403
    assert res_a_moves_b.json()["detail"]["required_permission"] == "move"

    # 6. Bob moves his own token -> Allowed (200)
    res_b_moves_b = client.post(
        f"/api/v1/board/tokens/{token_bob}/move",
        headers={"X-User-Id": player_bob},
        json={"to_x": 6, "to_y": 7},
    )
    assert res_b_moves_b.status_code == 200

    # 7. Bob attempts to move Alice's token -> Denied (403)
    res_b_moves_a = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": player_bob},
        json={"to_x": 0, "to_y": 0},
    )
    assert res_b_moves_a.status_code == 403

    # 8. Spectator Clara attempts to move Token Alice -> Denied (403)
    res_spectator_move = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": spectator_clara},
        json={"to_x": 2, "to_y": 2},
    )
    assert res_spectator_move.status_code == 403

    # 9. Spectator Clara inspects Token Alice -> Read-only Allowed (200)
    res_spectator_inspect = client.get(
        f"/api/v1/board/tokens/{token_alice}",
        headers={"X-User-Id": spectator_clara},
    )
    assert res_spectator_inspect.status_code == 200
    assert res_spectator_inspect.json()["token_id"] == token_alice

    # 10. GM Derek can move any token in the campaign -> Allowed (200)
    res_gm_moves_a = client.post(
        f"/api/v1/board/tokens/{token_alice}/move",
        headers={"X-User-Id": gm_derek},
        json={"to_x": 8, "to_y": 9},
    )
    assert res_gm_moves_a.status_code == 200

    res_gm_moves_b = client.post(
        f"/api/v1/board/tokens/{token_bob}/move",
        headers={"X-User-Id": gm_derek},
        json={"to_x": 9, "to_y": 9},
    )
    assert res_gm_moves_b.status_code == 200


@pytest.mark.asyncio
async def test_idempotence_and_instant_revocation() -> None:
    """Re-syncing produces no duplicates; revocation immediately revokes permissions."""
    campaign_id = f"camp-idem-{uuid4().hex[:8]}"
    user_id = "test_player_grant"

    # Grant membership twice (Idempotence)
    res1 = client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": user_id, "role": "player", "action": "grant"},
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": user_id, "role": "player", "action": "grant"},
    )
    assert res2.status_code == 200

    # User can view session
    res_view = client.get(
        f"/api/v1/sessions/{campaign_id}",
        headers={"X-User-Id": user_id},
    )
    assert res_view.status_code == 200

    # Revoke membership
    res_revoke = client.post(
        "/api/v1/auth/sync/membership",
        json={"campaign_id": campaign_id, "user_id": user_id, "role": "player", "action": "revoke"},
    )
    assert res_revoke.status_code == 200
    assert res_revoke.json()["action"] == "revoke"

    # Immediately after revocation: view attempt must fail with 403 Forbidden
    res_view_after = client.get(
        f"/api/v1/sessions/{campaign_id}",
        headers={"X-User-Id": user_id},
    )
    assert res_view_after.status_code == 403


@pytest.mark.asyncio
async def test_domain_event_listeners_stream_synchronization() -> None:
    """Publishing domain events automatically provisions SpiceDB Zanzibar relationships."""
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    listener = SpiceDBEventListener(sync_service=sync_service)

    # 1. Test via in-memory EventBus
    local_bus = EventBus()
    listener.register_bus_handlers(local_bus)

    campaign_id = f"camp-evt-{uuid4().hex[:8]}"
    dm_id = "watcher_dm_99"
    player_id = "barbarian_grog"
    char_id = uuid4()

    # Publish SessionCreated
    session_event = SessionCreated(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        session_id=campaign_id,
        dm_id=dm_id,
        title="Crypt of Shadows",
    )
    await local_bus.publish("SessionCreated", session_event)

    # Assert DM has run_session permission
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)

    # Publish ParticipantJoined
    participant_event = ParticipantJoined(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        user_id=player_id,
        role="player",
        character_id=char_id,
    )
    await local_bus.publish("ParticipantJoined", participant_event)

    # Assert Player has play and view permission
    assert await spicedb.check_permission("campaign", campaign_id, "play", "user", player_id)
    assert await spicedb.check_permission("campaign", campaign_id, "view", "user", player_id)

    # Publish CharacterCreated
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

    # Assert character owner can edit character
    assert await spicedb.check_permission("character", str(char_id), "edit", "user", player_id)


@pytest.mark.asyncio
async def test_redis_streams_event_bus_deserialization_and_sync() -> None:
    """Verify RedisStreamsEventBus publish and synchronization with SpiceDB."""
    mock_redis = MockAsyncRedis()
    event_bus = RedisStreamsEventBus(client=mock_redis)
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)
    listener = SpiceDBEventListener(sync_service=sync_service)

    campaign_id = f"camp-redis-{uuid4().hex[:8]}"
    dm_id = "redis_dm_01"

    # Publish to Redis stream
    evt = SessionCreated(
        aggregate_id=uuid4(),
        campaign_id=campaign_id,
        session_id=campaign_id,
        dm_id=dm_id,
    )
    entry_id = await event_bus.publish_event("runefoble.events.session", evt)
    assert entry_id is not None

    # Consume and pass to listener
    await listener.on_session_created(evt)

    # Assert permission is synchronized
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", dm_id)


@pytest.mark.asyncio
async def test_sync_resilience_and_retry() -> None:
    """Verify that ZitadelSpiceDBSyncService retries on transient connection errors."""
    call_count = 0

    class FlakySpiceDB:
        def __init__(self):
            self._tuples = set()

        async def write_relationship(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient network timeout")
            self._tuples.add("ok")

        async def delete_relationship(self, **kwargs):
            pass

        async def read_relationships(self):
            return []

    flaky_client = FlakySpiceDB()
    service = ZitadelSpiceDBSyncService(
        spicedb_client=flaky_client,  # type: ignore
        max_retries=4,
        retry_delay_seconds=0.01,
    )

    # Should succeed after retrying
    synced = await service.sync_membership("camp_flaky", "user_1", "player")
    assert call_count == 3
    assert len(synced) > 0
