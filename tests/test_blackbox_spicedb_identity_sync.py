"""Blackbox TDD frontdoor suite for SpiceDB identity and campaign role synchronization.

Verifies:
1. Frontdoor sync health endpoint (/api/v1/auth/sync/health).
2. User registration and OIDC claim synchronization into Zanzibar tuples.
3. GM role synchronization, DM override, and campaign atmosphere updates.
4. Idempotent relationship writes and instant permission revocation.
5. Redis Streams domain event bus deserialization and SessionCreated sync.
6. Transient fault resilience and exponential backoff retry logic.
"""

import os
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events.events import SessionCreated
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis


@pytest.fixture
def client(game_session_upstream) -> Iterator[TestClient]:
    """Enter the gateway lifespan after game_session is served, so proxied routes work."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def test_sync_health_frontdoor(client) -> None:
    """GET /api/v1/auth/sync/health reports operational status and SpiceDB connectivity."""
    res = client.get("/api/v1/auth/sync/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy" and data["spicedb_connected"] is True
    assert data["sync_service"] == "operational"


def test_sync_user_route_is_removed(trusted_ws_issuer, client) -> None:
    """POST /api/v1/auth/sync/user is gone. Token roles never write SpiceDB relations (TASK-0534)."""
    campaign_id = f"camp-sync-{uuid4().hex[:8]}"
    user_id = f"user-{uuid4().hex[:8]}"
    body = {"user_id": user_id, "roles": ["owner"], "campaign_id": campaign_id}
    token = trusted_ws_issuer.mint(user_id, extra_claims={"roles": ["owner"]})

    assert client.post("/api/v1/auth/sync/user", json=body).status_code == 404
    assert (
        client.post(
            "/api/v1/auth/sync/user",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 404
    )


def _bearer(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_campaign_as_owner(client: TestClient, issuer, owner_sub: str) -> str:
    """Create a campaign through the public route. The creator becomes its owner."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Sync Campaign"},
        headers=_bearer(issuer, owner_sub),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_gm_synchronization_dm_override_and_atmosphere(trusted_ws_issuer, client) -> None:
    """Synchronized GM can execute DM override and update campaign atmosphere."""
    spicedb = get_spicedb_client()
    owner_id = "owner_arthur"
    gm_id = "gm_elena"
    stranger_id = "stranger_pete"
    campaign_id = _create_campaign_as_owner(client, trusted_ws_issuer, owner_id)
    session_id = _owner_session(campaign_id, _bearer(trusted_ws_issuer, owner_id))

    # 1. Before sync: GM and stranger are rejected with 403
    res_before = client.post(
        f"/api/v1/sessions/{session_id}/dm-override",
        headers=_bearer(trusted_ws_issuer, gm_id),
        json={"action": "pause_encounter", "reason": "DM bathroom break"},
    )
    assert res_before.status_code == 403

    # 2. Owner grants the DM role through the public roles frontdoor
    res_sync = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": gm_id, "role": "dungeon_master"},
        headers=_bearer(trusted_ws_issuer, owner_id),
    )
    assert res_sync.status_code == 200
    assert res_sync.json()["status"] == "role_assigned"

    # 3. Assert observable permission via SpiceDBClient
    assert await spicedb.check_permission("campaign", campaign_id, "run_session", "user", gm_id)

    # 4. Synchronized GM can execute DM override
    res_override = client.post(
        f"/api/v1/sessions/{session_id}/dm-override",
        headers=_bearer(trusted_ws_issuer, gm_id),
        json={"action": "pause_encounter", "reason": "DM narrative pause"},
    )
    assert res_override.status_code == 200
    assert res_override.json()["dm_overrides"][-1]["action"] == "pause_encounter"

    # 5. Synchronized GM can update campaign atmosphere
    atmo_payload = {
        "location_name": "Tomb of the Lich King",
        "lighting": "Eerie Luminescence",
        "mood": "Suspenseful",
        "description": "Green spectral mist creeps through ancient flagstones.",
    }
    res_atmo = client.post(
        f"/api/v1/sessions/{session_id}/atmosphere",
        headers=_bearer(trusted_ws_issuer, gm_id),
        json=atmo_payload,
    )
    assert res_atmo.status_code == 200
    assert res_atmo.json()["atmosphere"]["location_name"] == "Tomb of the Lich King"

    # 6. Unassigned stranger is denied on both endpoints
    res_stranger_override = client.post(
        f"/api/v1/sessions/{session_id}/dm-override",
        headers=_bearer(trusted_ws_issuer, stranger_id),
        json={"action": "end_session"},
    )
    assert res_stranger_override.status_code == 403

    res_stranger_atmo = client.post(
        f"/api/v1/sessions/{session_id}/atmosphere",
        headers=_bearer(trusted_ws_issuer, stranger_id),
        json={"location_name": "Sunny Meadow"},
    )
    assert res_stranger_atmo.status_code == 403


@pytest.mark.asyncio
async def test_idempotence_and_instant_revocation(trusted_ws_issuer, client) -> None:
    """Re-granting produces no duplicates; removal immediately revokes permissions."""
    owner_id = "owner_idem"
    campaign_id = _create_campaign_as_owner(client, trusted_ws_issuer, owner_id)
    session_id = _owner_session(campaign_id, _bearer(trusted_ws_issuer, owner_id))
    user_id = "test_player_grant"
    owner_headers = _bearer(trusted_ws_issuer, owner_id)
    grant_payload = {"user_id": user_id, "role": "player"}

    assert (
        client.post(
            f"/api/v1/campaigns/{campaign_id}/roles", json=grant_payload, headers=owner_headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/campaigns/{campaign_id}/roles", json=grant_payload, headers=owner_headers
        ).status_code
        == 200
    )

    # User can view session
    assert (
        client.get(
            f"/api/v1/sessions/{session_id}", headers=_bearer(trusted_ws_issuer, user_id)
        ).status_code
        == 200
    )

    # Owner removes the member through the public members frontdoor
    res_revoke = client.delete(
        f"/api/v1/campaigns/{campaign_id}/members/{user_id}", headers=owner_headers
    )
    assert res_revoke.status_code == 200 and res_revoke.json()["status"] == "member_removed"

    # Immediately after revocation: view attempt must fail with 403 Forbidden
    assert (
        client.get(
            f"/api/v1/sessions/{session_id}", headers=_bearer(trusted_ws_issuer, user_id)
        ).status_code
        == 403
    )


@pytest.mark.asyncio
async def test_redis_streams_event_bus_deserialization_and_sync(client) -> None:
    """Verify RedisStreamsEventBus publish and synchronization with SpiceDB."""
    mock_redis = MockAsyncRedis()
    event_bus = RedisStreamsEventBus(client=mock_redis)
    spicedb = get_spicedb_client()
    sync_service = ZitadelSpiceDBSyncService(spicedb_client=spicedb)

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

    # Pass the consumed event to the sync service
    await sync_service.handle_session_created(evt)

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


def _owner_session(campaign_id: str, headers: dict[str, str]) -> str:
    """Create a game session in a campaign through the owner's public game_session route."""
    url = os.environ["RUNEFOBLE_GAME_SESSION_URL"]
    res = httpx.post(
        f"{url}/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Crypt"},
        headers=headers,
        timeout=5.0,
    )
    assert res.status_code == 200, res.text
    return res.json()["session_id"]
