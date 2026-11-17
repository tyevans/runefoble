"""Blackbox TDD suite for TASK-0612: Silo upload fails closed and the asset index is durable.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup) and ADR-0007.
Setup and assertions use only public HTTP routes, the Silo HTTP boundary (FakeSilo),
and published CloudEvents on the Redis Streams bus. No test writes private state.
"""

from __future__ import annotations

import pytest
from asset_forge.dependencies import set_event_bus
from asset_forge.main import app as asset_forge_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.storage import SiloStorageService, get_storage_service, set_storage_service

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES, SILO_TEST_ENDPOINT, FakeSilo

BATTLEMAP_BODY = {
    "prompt": "Flooded crypt with sunken altars",
    "width_cells": 10,
    "height_cells": 10,
}
ASSET_STREAM = "runefoble.events.asset"


@pytest.fixture
def forge_client() -> TestClient:
    return TestClient(asset_forge_app)


@pytest.fixture
def redis_stream() -> MockAsyncRedis:
    mock_redis = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=mock_redis))
    yield mock_redis
    set_event_bus(None)


def test_battlemap_forge_fails_closed_when_silo_unreachable(
    forge_client: TestClient, silo_double: FakeSilo, redis_stream: MockAsyncRedis
):
    """POST battlemap with Silo down returns 503, creates no asset id and publishes nothing."""
    silo_double.outage = True

    response = forge_client.post("/api/v1/forge/battlemap", json=BATTLEMAP_BODY)

    assert response.status_code == 503, response.text
    assert "asset_id" not in response.json()
    assert silo_double.objects == {}
    assert redis_stream.streams.get(ASSET_STREAM, []) == []


def test_token_forge_fails_closed_when_silo_returns_server_error(
    forge_client: TestClient, silo_double: FakeSilo, redis_stream: MockAsyncRedis
):
    """POST token with Silo answering 500 returns 503 and records no forged asset."""
    silo_double.forced_status = 500

    response = forge_client.post(
        "/api/v1/forge/token",
        json={"token_name": "Ghoul", "prompt": "Gaunt ghoul with rusted claws"},
    )

    assert response.status_code == 503, response.text
    assert "asset_id" not in response.json()
    assert silo_double.objects == {}
    assert redis_stream.streams.get(ASSET_STREAM, []) == []


def test_gateway_upload_fails_closed_when_silo_unreachable(silo_double: FakeSilo, signing_issuer):
    """Gateway avatar upload with Silo down returns 503 and stores nothing."""
    silo_double.outage = True
    gateway_client = TestClient(
        gateway_app,
        headers={"Authorization": f"Bearer {signing_issuer.mint('player-valeros')}"},
    )

    response = gateway_client.post(
        "/api/v1/assets/upload",
        files={"file": ("crest.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"asset_type": "avatar"},
    )

    assert response.status_code == 503, response.text
    assert silo_double.objects == {}


def test_forged_battlemap_is_retrievable_after_service_restart(silo_double: FakeSilo):
    """A battlemap confirmed by Silo stays retrievable by a fresh app and storage client."""
    first_client = TestClient(asset_forge_app)
    created = first_client.post("/api/v1/forge/battlemap", json=BATTLEMAP_BODY)
    assert created.status_code == 200, created.text
    asset_id = created.json()["asset_id"]

    # Simulate a restart: new HTTP client and a new Silo client on the same Silo endpoint.
    restarted_silo = SiloStorageService(
        endpoint=SILO_TEST_ENDPOINT,
        secure=False,
        bucket_assets="runefoble-assets",
        transport=silo_double.transport(),
    )
    previous = get_storage_service()
    set_storage_service(restarted_silo)
    try:
        restarted_client = TestClient(asset_forge_app)
        fetched = restarted_client.get(f"/api/v1/forge/battlemap/{asset_id}")
    finally:
        set_storage_service(previous)

    assert fetched.status_code == 200, fetched.text
    meta = fetched.json()
    assert meta["asset_id"] == asset_id
    assert meta["object_key"] == f"battlemaps/{asset_id}.png"
    assert meta["bucket"] == "runefoble-assets"
