"""Blackbox TDD test suite for Asset Forge Auth, Events & API Contracts (TASK-0092).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Published standard CloudEvents over Redis Streams (BattlemapForged, TokenAssetForged)
- Object-level Zanzibar authorization via SpiceDB schema
- Asset metadata retrieval, 404 behavior, and request input validation
- Healthz, OpenAPI hub registration, and UI microfrontend manifest
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from asset_forge.dependencies import get_forge_repo, get_spicedb_client, get_storage, set_event_bus
from asset_forge.main import app
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events import BattlemapForged, TokenAssetForged
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and bus states before and after each test."""
    storage = get_storage()
    storage.clear()
    set_event_bus(None)
    yield
    storage.clear()
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_asset_forge_cloudevents_registration():
    """Verify BattlemapForged and TokenAssetForged are registered in eventsource EventRegistry."""
    assert get_event_class_or_none("runefoble.events.asset.battlemap_forged") is BattlemapForged
    assert get_event_class_or_none("runefoble.events.asset.token_forged") is TokenAssetForged
    assert get_event_class_or_none("BattlemapForged") is BattlemapForged
    assert get_event_class_or_none("BattlemapCreated") is BattlemapForged
    assert get_event_class_or_none("TokenAssetForged") is TokenAssetForged
    assert get_event_class_or_none("AssetGenerated") is TokenAssetForged

    event = BattlemapForged(
        asset_id="map-12345",
        creator_id="dm-evelyn",
        prompt="Subterranean dwarven forge with lava canals",
        image_url="http://silo:9000/runefoble-assets/battlemaps/map-12345.png",
        width_cells=20,
        height_cells=20,
        cell_size_px=64,
        wall_segments_count=12,
        hazard_cells_count=4,
        doors_count=2,
        theme="dwarven_forge",
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.asset.battlemap_forged"
    assert ce["data"]["asset_id"] == "map-12345"
    assert ce["data"]["theme"] == "dwarven_forge"
    assert ce["data"]["width_cells"] == 20


@pytest.mark.asyncio
async def test_blackbox_event_publication_to_redis_streams_and_event_sourcing(client: TestClient):
    """Verify BattlemapForged & TokenAssetForged published over Redis Streams & recorded in aggregate."""
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)

    mem_events: list[Any] = []

    async def on_mem_event(event: Any):
        mem_events.append(event)

    platform_bus.subscribe("runefoble.events.asset.battlemap_forged", on_mem_event)
    platform_bus.subscribe("runefoble.events.asset.token_forged", on_mem_event)

    campaign_id = uuid4()
    cid = str(campaign_id)
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=cid,
        relation="dungeon_master",
        subject_type="user",
        subject_id="dm-evelyn",
    )

    res_map = client.post(
        "/api/v1/forge/battlemap",
        json={"prompt": "Catacombs", "campaign_id": cid, "width_cells": 10, "height_cells": 10},
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert res_map.status_code == 200
    map_asset_id = res_map.json()["asset_id"]

    res_tok = client.post(
        "/api/v1/forge/token",
        json={
            "token_name": "Lich",
            "prompt": "Skeletal sorcerer",
            "token_type": "monster",
            "campaign_id": cid,
        },
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert res_tok.status_code == 200
    tok_asset_id = res_tok.json()["asset_id"]

    stream_entries = mock_redis.streams.get("runefoble.events.asset", [])
    assert len(stream_entries) == 2

    _, map_evt = stream_entries[0]
    assert map_evt["event_type"] == "runefoble.events.asset.battlemap_forged"
    assert map_asset_id in map_evt["payload"]
    assert "Catacombs" in map_evt["payload"]

    _, tok_evt = stream_entries[1]
    assert tok_evt["event_type"] == "runefoble.events.asset.token_forged"
    assert tok_asset_id in tok_evt["payload"]
    assert "Lich" in tok_evt["payload"]

    assert len(mem_events) == 2
    assert isinstance(mem_events[0], BattlemapForged)
    assert isinstance(mem_events[1], TokenAssetForged)

    repo = get_forge_repo()
    loaded_agg = await repo.load(campaign_id)
    assert map_asset_id in loaded_agg.state.forged_battlemaps
    assert tok_asset_id in loaded_agg.state.forged_tokens


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_authorization(client: TestClient):
    """Verify Zanzibar authorization enforces permissions on campaign-linked asset generation."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id = uuid4()
    authorized_dm = f"dm-{uuid4().hex[:6]}"
    unauthorized_user = f"stranger-{uuid4().hex[:6]}"

    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=str(campaign_id),
        relation="dungeon_master",
        subject_type="user",
        subject_id=authorized_dm,
    )

    res_auth = client.post(
        "/api/v1/forge/battlemap",
        json={"prompt": "Elven sanctuary treehouse in canopy", "campaign_id": str(campaign_id)},
        headers={"X-User-Id": authorized_dm},
    )
    assert res_auth.status_code == 200

    res_unauth = client.post(
        "/api/v1/forge/battlemap",
        json={"prompt": "Malicious fortress intrusion", "campaign_id": str(campaign_id)},
        headers={"X-User-Id": unauthorized_user},
    )
    assert res_unauth.status_code == 403
    assert "Forbidden" in res_unauth.json()["detail"]


def test_blackbox_get_metadata_and_not_found(client: TestClient):
    """Verify retrieving asset metadata and 404 behavior for non-existent IDs."""
    res = client.post(
        "/api/v1/forge/battlemap", json={"prompt": "Underdark mushroom cavern with spores"}
    )
    assert res.status_code == 200
    asset_id = res.json()["asset_id"]

    get_res = client.get(f"/api/v1/forge/battlemap/{asset_id}")
    assert get_res.status_code == 200
    meta = get_res.json()
    assert meta["asset_id"] == asset_id
    assert "battlemaps/" in meta["object_key"]

    missing_res = client.get("/api/v1/forge/battlemap/map-does-not-exist")
    assert missing_res.status_code == 404


def test_blackbox_health_openapi_and_ui_manifest(client: TestClient):
    """Verify /healthz, /openapi.json hub, and /ui/manifest endpoints."""
    h_res = client.get("/healthz")
    assert h_res.status_code == 200
    assert h_res.json() == {"status": "ok", "service": "asset_forge"}

    o_res = client.get("/openapi.json")
    assert o_res.status_code == 200
    paths = o_res.json()["paths"]
    assert "/api/v1/forge/battlemap" in paths
    assert "/api/v1/forge/token" in paths

    m_res = client.get("/ui/manifest")
    assert m_res.status_code == 200
    manifest = m_res.json()
    assert manifest["service"] == "asset_forge"
    assert manifest["package"] == "@runefoble/asset-forge-ui"
    assert "runefoble-asset-forge" in manifest["components"]


def test_blackbox_validation_rejections(client: TestClient):
    """Verify input validation errors for prompts and dimensions."""
    res_short = client.post("/api/v1/forge/battlemap", json={"prompt": "ab"})
    assert res_short.status_code == 422

    res_big = client.post(
        "/api/v1/forge/battlemap", json={"prompt": "Valid prompt", "width_cells": 60}
    )
    assert res_big.status_code == 422

    res_small = client.post(
        "/api/v1/forge/battlemap", json={"prompt": "Valid prompt", "height_cells": 3}
    )
    assert res_small.status_code == 422

    res_no_name = client.post(
        "/api/v1/forge/token", json={"prompt": "Valid prompt", "token_name": ""}
    )
    assert res_no_name.status_code == 422
