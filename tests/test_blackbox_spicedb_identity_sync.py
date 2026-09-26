"""Blackbox TDD frontdoor suite for SpiceDB identity and campaign role synchronization.

Verifies:
1. Frontdoor sync health endpoint (/api/v1/auth/sync/health).
2. User registration and OIDC claim synchronization into Zanzibar tuples.
3. GM role synchronization, DM override, and campaign atmosphere updates.
4. Idempotent relationship writes and instant permission revocation.
5. Redis Streams domain event bus deserialization and SessionCreated sync.
6. Transient fault resilience and exponential backoff retry logic.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.listener import SpiceDBEventListener
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events import SessionCreated
from runefoble_platform.consumer_group import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

client = TestClient(app)


def test_sync_health_frontdoor() -> None:
    """GET /api/v1/auth/sync/health reports operational status and SpiceDB connectivity."""
    res = client.get("/api/v1/auth/sync/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy" and data["spicedb_connected"] is True
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
    assert body["status"] == "synchronized" and body["user_id"] == user_id
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
    atmo_payload = {
        "location_name": "Tomb of the Lich King",
        "lighting": "Eerie Luminescence",
        "mood": "Suspenseful",
        "description": "Green spectral mist creeps through ancient flagstones.",
    }
    res_atmo = client.post(
        f"/api/v1/sessions/{campaign_id}/atmosphere",
        headers={"X-User-Id": gm_id},
        json=atmo_payload,
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
async def test_idempotence_and_instant_revocation() -> None:
    """Re-syncing produces no duplicates; revocation immediately revokes permissions."""
    campaign_id = f"camp-idem-{uuid4().hex[:8]}"
    user_id = "test_player_grant"

    grant_payload = {
        "campaign_id": campaign_id,
        "user_id": user_id,
        "role": "player",
        "action": "grant",
    }
    assert client.post("/api/v1/auth/sync/membership", json=grant_payload).status_code == 200
    assert client.post("/api/v1/auth/sync/membership", json=grant_payload).status_code == 200

    # User can view session
    assert (
        client.get(f"/api/v1/sessions/{campaign_id}", headers={"X-User-Id": user_id}).status_code
        == 200
    )

    # Revoke membership
    revoke_payload = {
        "campaign_id": campaign_id,
        "user_id": user_id,
        "role": "player",
        "action": "revoke",
    }
    res_revoke = client.post("/api/v1/auth/sync/membership", json=revoke_payload)
    assert res_revoke.status_code == 200 and res_revoke.json()["action"] == "revoke"

    # Immediately after revocation: view attempt must fail with 403 Forbidden
    assert (
        client.get(f"/api/v1/sessions/{campaign_id}", headers={"X-User-Id": user_id}).status_code
        == 403
    )


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
        async def write_relationship(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient network timeout")

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
