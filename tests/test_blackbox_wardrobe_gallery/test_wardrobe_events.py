"""Blackbox TDD tests for Wardrobe Variant Generative Synthesis, Silo S3 Storage, and CloudEvents.

Governed by:
- Hard Invariant 2: Domain state transitions and events powered by eventsource-py
- Hard Invariant 6: File length limit (< 500 lines; suite module < 200 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import struct

import pytest
from asset_forge.dependencies import get_storage as get_asset_storage
from asset_forge.dependencies import set_event_bus as set_forge_bus
from character_sheet.dependencies import (
    set_event_bus as set_char_bus,
)
from fastapi.testclient import TestClient
from runefoble_events import (
    BaseRunefobleEvent,
    CharacterDamaged,
    CharacterPortraitUpdated,
    PortraitVariantGenerated,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus

from .conftest import PNG_SIGNATURE


def test_blackbox_generative_wardrobe_synthesis_and_storage(
    forge_client: TestClient, char_client: TestClient
):
    """Verify generative wardrobe variant synthesis, Silo S3 storage, and character assignment."""
    # 1. Create character
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Nadia the Bard", "character_class": "Bard", "max_hp": 30},
    )
    char_id = create_res.json()["character_id"]

    # 2. Synthesize ballroom masquerade wardrobe variant via Asset Forge
    forge_res = forge_client.post(
        "/api/v1/forge/wardrobe",
        json={
            "character_id": char_id,
            "character_name": "Nadia the Bard",
            "attire_type": "ballroom_masquerade",
            "prompt": "Gilded Venetian mask and silk gown with sapphire brooch",
            "face_embedding_seed": "nadia_face_signature_123",
            "size_px": 256,
        },
        headers={"X-User-Id": "dm-nadia"},
    )
    assert forge_res.status_code == 200, forge_res.text
    forge_data = forge_res.json()
    assert forge_data["status"] == "forged"
    variant_id = forge_data["variant_id"]
    image_url = forge_data["image_url"]
    assert variant_id.startswith("var-")
    assert forge_data["attire_type"] == "ballroom_masquerade"

    # 3. Verify asset stored in Silo S3 storage
    storage = get_asset_storage()
    asset_bytes, content_type = storage.get_asset(
        storage.default_bucket, f"wardrobe/{variant_id}.png"
    )
    assert content_type == "image/png"
    assert asset_bytes.startswith(PNG_SIGNATURE)
    w, h = struct.unpack(">II", asset_bytes[16:24])
    assert w == 256
    assert h == 256

    # 4. Verify asset retrieval via GET /api/v1/forge/wardrobe/{variant_id}
    meta_res = forge_client.get(f"/api/v1/forge/wardrobe/{variant_id}")
    assert meta_res.status_code == 200
    assert meta_res.json()["asset_id"] == variant_id

    # 5. Add wardrobe variant to character sheet via frontdoor POST /api/v1/characters/{id}/wardrobe
    add_res = char_client.post(
        f"/api/v1/characters/{char_id}/wardrobe",
        json={
            "variant_id": variant_id,
            "variant_name": "Royal Masquerade Gown",
            "attire_type": "ballroom_masquerade",
            "image_url": image_url,
            "prompt": forge_data["prompt"],
            "set_active": True,
        },
    )
    assert add_res.status_code == 200
    add_data = add_res.json()
    assert variant_id in add_data["wardrobe_variants"]
    assert add_data["active_variant_id"] == variant_id
    assert add_data["base_portrait_url"] == image_url

    # 6. Verify GET /api/v1/characters/{id}/wardrobe
    list_res = char_client.get(f"/api/v1/characters/{char_id}/wardrobe")
    assert list_res.status_code == 200
    assert variant_id in list_res.json()

    # 7. Switch active portrait back to default or another variant
    switch_res = char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"variant_id": None, "image_url": "/assets/portraits/nadia-default.svg"},
    )
    assert switch_res.status_code == 200
    assert switch_res.json()["active_variant_id"] is None
    assert "/assets/portraits/nadia-default.svg" in switch_res.json()["base_portrait_url"]


@pytest.mark.asyncio
async def test_blackbox_event_dispatch(char_client: TestClient, forge_client: TestClient):
    """Verify CharacterDamaged, PortraitVariantGenerated, and CharacterPortraitUpdated stream events."""
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_char_bus(bus)
    set_forge_bus(bus)

    # a) Create character
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Nadia", "character_class": "Bard", "max_hp": 30},
    )
    char_id = create_res.json()["character_id"]

    # b) Damage character -> verifies CharacterDamaged event
    char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -8, "source": "Firebolt"},
    )

    # c) Forge wardrobe variant -> verifies PortraitVariantGenerated event
    forge_client.post(
        "/api/v1/forge/wardrobe",
        json={
            "character_id": char_id,
            "character_name": "Nadia",
            "attire_type": "arctic_tundra",
        },
    )

    # d) Add wardrobe to character sheet -> verifies PortraitVariantGenerated on character stream
    char_client.post(
        f"/api/v1/characters/{char_id}/wardrobe",
        json={
            "variant_id": "var-arctic-001",
            "variant_name": "Arctic Coat",
            "attire_type": "arctic_tundra",
            "image_url": "/assets/portraits/arctic-nadia.svg",
        },
    )

    # e) Set active portrait -> verifies CharacterPortraitUpdated event
    char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"image_url": "/assets/portraits/arctic-nadia.svg"},
    )

    char_stream = mock_redis.streams.get("runefoble.events.character", [])
    char_event_types = [entry[1]["event_type"] for entry in char_stream]

    asset_stream = mock_redis.streams.get("runefoble.events.asset", [])
    asset_event_types = [entry[1]["event_type"] for entry in asset_stream]

    assert issubclass(CharacterDamaged, BaseRunefobleEvent)
    assert issubclass(PortraitVariantGenerated, BaseRunefobleEvent)
    assert issubclass(CharacterPortraitUpdated, BaseRunefobleEvent)

    assert "runefoble.events.character.damaged" in char_event_types
    assert "runefoble.events.character.portrait_variant_generated" in char_event_types
    assert "runefoble.events.character.portrait_updated" in char_event_types
    assert "runefoble.events.character.portrait_variant_generated" in asset_event_types
