"""Blackbox TDD test suite for Procedural Battlemap & Token Asset Forge (TASK-0049).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in asset_forge.main
- Silo S3 storage retrieval and validation
- Published standard CloudEvents over Redis Streams (BattlemapForged, TokenAssetForged)
- Object-level Zanzibar authorization via SpiceDB schema
"""

from __future__ import annotations

import struct
from typing import Any
from uuid import uuid4

import pytest
from asset_forge.dependencies import (
    get_forge_repo,
    get_spicedb_client,
    get_storage,
    set_event_bus,
)
from asset_forge.main import app
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events import (
    BattlemapForged,
    TokenAssetForged,
)
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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


# ---------------------------------------------------------------------------
# 1. Event Registration & CloudEvents Compliance Tests
# ---------------------------------------------------------------------------


def test_asset_forge_cloudevents_registration():
    """Verify BattlemapForged and TokenAssetForged are registered in eventsource EventRegistry."""
    bm_cls = get_event_class_or_none("runefoble.events.asset.battlemap_forged")
    assert bm_cls is not None
    assert bm_cls is BattlemapForged

    tok_cls = get_event_class_or_none("runefoble.events.asset.token_forged")
    assert tok_cls is not None
    assert tok_cls is TokenAssetForged

    # Verify short names and backward-compatible aliases
    assert get_event_class_or_none("BattlemapForged") is BattlemapForged
    assert get_event_class_or_none("BattlemapCreated") is BattlemapForged
    assert get_event_class_or_none("TokenAssetForged") is TokenAssetForged
    assert get_event_class_or_none("AssetGenerated") is TokenAssetForged

    # Verify CloudEvents serialization
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


# ---------------------------------------------------------------------------
# 2. Blackbox Procedural Battlemap Generation & Geometry Extraction
# ---------------------------------------------------------------------------


def test_blackbox_forge_battlemap_generation_and_storage(client: TestClient):
    """Verify POST /api/v1/forge/battlemap generates map, extracts geometry, and stores in Silo S3."""
    response = client.post(
        "/api/v1/forge/battlemap",
        json={
            "prompt": "Subterranean dwarven forge with lava canals and broken anvil statues",
            "width_cells": 16,
            "height_cells": 16,
            "cell_size_px": 64,
            "wall_density": 0.25,
            "hazard_density": 0.15,
        },
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Output model verification
    assert data["status"] == "forged"
    assert data["asset_id"].startswith("map-")
    assert data["theme"] == "dwarven_forge"
    assert data["width_cells"] == 16
    assert data["height_cells"] == 16
    assert data["cell_size_px"] == 64

    # 2. Spatial geometry analysis
    assert len(data["wall_segments"]) > 0
    assert len(data["doors"]) > 0
    assert len(data["hazard_cells"]) > 0

    # Verify dwarven forge theme produced lava hazards with 2d10 damage
    first_hazard = data["hazard_cells"][0]
    assert first_hazard["hazard_type"] == "lava"
    assert first_hazard["damage_dice"] == "2d10"
    assert first_hazard["terrain_type"] == "difficult"

    # 3. Board state pre-calculated payload
    geom = data["board_geometry_payload"]
    assert "terrain_mutations" in geom
    assert "obstacle_tokens" in geom
    assert "wall_segments" in geom
    assert "doors" in geom
    assert len(geom["terrain_mutations"]) == len(data["hazard_cells"])

    # 4. Storage verification directly from Silo S3
    storage = get_storage()
    asset_bytes, content_type = storage.get_asset(
        "runefoble-assets", f"battlemaps/{data['asset_id']}.png"
    )
    assert content_type == "image/png"
    assert asset_bytes.startswith(PNG_SIGNATURE)

    # Verify PNG dimensions match 16 * 64 = 1024 px
    w, h = struct.unpack(">II", asset_bytes[16:24])
    assert w == 16 * 64
    assert h == 16 * 64


# ---------------------------------------------------------------------------
# 3. Blackbox Token Portrait Generation with Circular Transparency
# ---------------------------------------------------------------------------


def test_blackbox_forge_token_portrait_and_transparency(client: TestClient):
    """Verify POST /api/v1/forge/token creates circular transparent token portrait in Silo S3."""
    response = client.post(
        "/api/v1/forge/token",
        json={
            "token_name": "Thorin Ironbreaker",
            "prompt": "Dwarven paladin with glowing runic warhammer",
            "token_type": "pc",
            "size_px": 128,
            "crop_style": "circular",
            "border_color": "#e63946",
            "border_width": 6,
            "transparent_background": True,
        },
        headers={"X-User-Id": "player-marcus"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "forged"
    assert data["asset_id"].startswith("tok-")
    assert data["token_name"] == "Thorin Ironbreaker"
    assert data["token_type"] == "pc"
    assert data["crop_style"] == "circular"
    assert data["size_px"] == 128
    assert data["has_transparency"] is True

    # Storage verification
    storage = get_storage()
    asset_bytes, content_type = storage.get_asset(
        "runefoble-assets", f"tokens/{data['asset_id']}.png"
    )
    assert content_type == "image/png"
    assert asset_bytes.startswith(PNG_SIGNATURE)

    w, h = struct.unpack(">II", asset_bytes[16:24])
    assert w == 128
    assert h == 128


# ---------------------------------------------------------------------------
# 4. Domain Event Publication to Redis Streams & In-Memory Bus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_event_publication_to_redis_streams_and_event_sourcing(client: TestClient):
    """Verify BattlemapForged & TokenAssetForged are published over Redis Streams & recorded in aggregate."""
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)

    mem_events: list[Any] = []

    async def on_mem_event(event: Any):
        mem_events.append(event)

    platform_bus.subscribe("runefoble.events.asset.battlemap_forged", on_mem_event)
    platform_bus.subscribe("runefoble.events.asset.token_forged", on_mem_event)

    campaign_id = uuid4()
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=str(campaign_id),
        relation="dungeon_master",
        subject_type="user",
        subject_id="dm-evelyn",
    )

    # 1. Forge battlemap
    res_map = client.post(
        "/api/v1/forge/battlemap",
        json={
            "prompt": "Ancient catacombs with necrotic spikes and sarcophagi",
            "campaign_id": str(campaign_id),
            "width_cells": 10,
            "height_cells": 10,
        },
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert res_map.status_code == 200
    map_asset_id = res_map.json()["asset_id"]

    # 2. Forge token
    res_tok = client.post(
        "/api/v1/forge/token",
        json={
            "token_name": "Lich King",
            "prompt": "Undead skeletal sorcerer",
            "token_type": "monster",
            "campaign_id": str(campaign_id),
        },
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert res_tok.status_code == 200
    tok_asset_id = res_tok.json()["asset_id"]

    # Check Redis Streams events
    stream_entries = mock_redis.streams.get("runefoble.events.asset", [])
    assert len(stream_entries) == 2

    # First event: battlemap forged
    _, map_evt = stream_entries[0]
    assert map_evt["event_type"] == "runefoble.events.asset.battlemap_forged"
    assert map_asset_id in map_evt["payload"]
    assert "Ancient catacombs" in map_evt["payload"]

    # Second event: token forged
    _, tok_evt = stream_entries[1]
    assert tok_evt["event_type"] == "runefoble.events.asset.token_forged"
    assert tok_asset_id in tok_evt["payload"]
    assert "Lich King" in tok_evt["payload"]

    # Check in-memory bus events
    assert len(mem_events) == 2
    assert isinstance(mem_events[0], BattlemapForged)
    assert isinstance(mem_events[1], TokenAssetForged)

    # 3. Check event-sourced aggregate state reconstitution
    repo = get_forge_repo()
    loaded_agg = await repo.load(campaign_id)
    assert map_asset_id in loaded_agg.state.forged_battlemaps
    assert tok_asset_id in loaded_agg.state.forged_tokens


# ---------------------------------------------------------------------------
# 5. SpiceDB Zanzibar Authorization Checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_authorization(client: TestClient):
    """Verify Zanzibar authorization enforces permissions on campaign-linked asset generation."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id = uuid4()
    authorized_dm = f"dm-{uuid4().hex[:6]}"
    unauthorized_user = f"stranger-{uuid4().hex[:6]}"

    # Grant run_session to authorized DM in SpiceDB
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=str(campaign_id),
        relation="dungeon_master",
        subject_type="user",
        subject_id=authorized_dm,
    )

    # 1. Authorized DM succeeds
    res_auth = client.post(
        "/api/v1/forge/battlemap",
        json={
            "prompt": "Elven sanctuary treehouse in the canopy",
            "campaign_id": str(campaign_id),
        },
        headers={"X-User-Id": authorized_dm},
    )
    assert res_auth.status_code == 200

    # 2. Unauthorized stranger is rejected with 403 Forbidden
    res_unauth = client.post(
        "/api/v1/forge/battlemap",
        json={
            "prompt": "Malicious fortress intrusion",
            "campaign_id": str(campaign_id),
        },
        headers={"X-User-Id": unauthorized_user},
    )
    assert res_unauth.status_code == 403
    assert "Forbidden" in res_unauth.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Metadata Query and 404 Validation
# ---------------------------------------------------------------------------


def test_blackbox_get_metadata_and_not_found(client: TestClient):
    """Verify retrieving asset metadata and 404 behavior for non-existent IDs."""
    # 1. Generate map
    res = client.post(
        "/api/v1/forge/battlemap",
        json={"prompt": "Underdark mushroom cavern with spores"},
    )
    assert res.status_code == 200
    asset_id = res.json()["asset_id"]

    # 2. Fetch metadata via GET
    get_res = client.get(f"/api/v1/forge/battlemap/{asset_id}")
    assert get_res.status_code == 200
    meta = get_res.json()
    assert meta["asset_id"] == asset_id
    assert "battlemaps/" in meta["object_key"]

    # 3. Non-existent asset returns 404
    missing_res = client.get("/api/v1/forge/battlemap/map-does-not-exist")
    assert missing_res.status_code == 404


# ---------------------------------------------------------------------------
# 7. Health, OpenAPI, and Microfrontend Manifest Verification
# ---------------------------------------------------------------------------


def test_blackbox_health_openapi_and_ui_manifest(client: TestClient):
    """Verify /healthz, /openapi.json hub, and /ui/manifest endpoints."""
    # Health check
    h_res = client.get("/healthz")
    assert h_res.status_code == 200
    assert h_res.json() == {"status": "ok", "service": "asset_forge"}

    # OpenAPI schema discovery
    o_res = client.get("/openapi.json")
    assert o_res.status_code == 200
    paths = o_res.json()["paths"]
    assert "/api/v1/forge/battlemap" in paths
    assert "/api/v1/forge/token" in paths

    # UI Manifest discovery
    m_res = client.get("/ui/manifest")
    assert m_res.status_code == 200
    manifest = m_res.json()
    assert manifest["service"] == "asset_forge"
    assert manifest["package"] == "@runefoble/asset-forge-ui"
    assert "runefoble-asset-forge" in manifest["components"]


# ---------------------------------------------------------------------------
# 8. Request Validation and Bounds Checking
# ---------------------------------------------------------------------------


def test_blackbox_validation_rejections(client: TestClient):
    """Verify input validation errors for prompts and dimensions."""
    # 1. Battlemap with too-short prompt
    res_short = client.post("/api/v1/forge/battlemap", json={"prompt": "ab"})
    assert res_short.status_code == 422

    # 2. Battlemap with dimensions exceeding bounds (ge=5, le=50)
    res_too_big = client.post(
        "/api/v1/forge/battlemap",
        json={"prompt": "Valid battlemap prompt", "width_cells": 60},
    )
    assert res_too_big.status_code == 422

    res_too_small = client.post(
        "/api/v1/forge/battlemap",
        json={"prompt": "Valid battlemap prompt", "height_cells": 3},
    )
    assert res_too_small.status_code == 422

    # 3. Token with empty name
    res_no_name = client.post(
        "/api/v1/forge/token",
        json={"prompt": "Valid prompt", "token_name": ""},
    )
    assert res_no_name.status_code == 422
