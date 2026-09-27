"""Blackbox TDD test suite for Generative Character Wardrobe & Portrait Gallery (TASK-0124).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in character_sheet and asset_forge
- Silo S3 object storage validation
- Published standard CloudEvents over Redis Streams (CharacterDamaged, PortraitVariantGenerated, CharacterPortraitUpdated)
- Object-level Zanzibar authorization via SpiceDB schema
- Microfrontend manifest advertising and Storybook stories verification
"""

from __future__ import annotations

import struct
from pathlib import Path
from uuid import uuid4

import pytest
from asset_forge.dependencies import get_storage as get_asset_storage
from asset_forge.dependencies import set_event_bus as set_forge_bus
from asset_forge.main import app as asset_forge_app
from character_sheet.dependencies import (
    get_spicedb_client as get_char_spicedb,
)
from character_sheet.dependencies import (
    set_event_bus as set_char_bus,
)
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events import (
    BaseRunefobleEvent,
    CharacterDamaged,
    CharacterPortraitUpdated,
    PortraitVariantGenerated,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and bus states before and after each test."""
    storage = get_asset_storage()
    storage.clear()
    set_char_bus(None)
    set_forge_bus(None)
    yield
    storage.clear()
    set_char_bus(None)
    set_forge_bus(None)


@pytest.fixture
def char_client() -> TestClient:
    return TestClient(character_app)


@pytest.fixture
def forge_client() -> TestClient:
    return TestClient(asset_forge_app)


def test_blackbox_condition_overlays_and_bloodied_threshold(char_client: TestClient):
    """Verify HP drop below 50% triggers bloodied badge and dynamic SVG condition overlay."""
    # 1. Create character via frontdoor POST /api/v1/characters
    create_res = char_client.post(
        "/api/v1/characters",
        json={
            "name": "Nadia the Expressive Bard",
            "character_class": "Bard",
            "max_hp": 40,
            "personality_traits": ["dramatic", "poetic"],
        },
    )
    assert create_res.status_code == 200
    char_data = create_res.json()
    char_id = char_data["character_id"]
    assert char_data["current_hp"] == 40
    assert "bloodied" not in char_data["condition_badges"]

    # 2. Inflict minor damage (30/40 HP = 75% HP) -> still healthy
    hp1_res = char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -10, "source": "Goblin Dagger"},
    )
    assert hp1_res.status_code == 200
    hp1_data = hp1_res.json()
    assert hp1_data["current_hp"] == 30
    assert "bloodied" not in hp1_data["condition_badges"]

    # 3. Inflict injury crossing the 50% HP threshold (18/40 HP = 45% HP)
    hp2_res = char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -12, "source": "Manticore Spike"},
    )
    assert hp2_res.status_code == 200
    hp2_data = hp2_res.json()
    assert hp2_data["current_hp"] == 18
    # DoD Requirement 1: Character sheet REST API returns bloodied badge and updated portrait URL
    assert "bloodied" in hp2_data["condition_badges"]
    assert "data:image/svg+xml" in hp2_data["active_portrait_url"]

    # 4. Frontdoor GET /api/v1/characters/{id}/portrait
    port_res = char_client.get(f"/api/v1/characters/{char_id}/portrait")
    assert port_res.status_code == 200
    port_data = port_res.json()
    assert "bloodied" in port_data["condition_badges"]
    assert port_data["current_hp"] == 18
    assert "bloodied-vignette" in port_data["svg_overlay"]
    assert "blood-scratches" in port_data["svg_overlay"]

    # 5. Healing back above 50% (28/40 HP = 70% HP) clears the bloodied badge
    heal_res = char_client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": 10, "source": "Cure Wounds"},
    )
    assert heal_res.status_code == 200
    heal_data = heal_res.json()
    assert heal_data["current_hp"] == 28
    assert "bloodied" not in heal_data["condition_badges"]


def test_blackbox_status_affliction_overlays(char_client: TestClient):
    """Verify condition affliction (poisoned, stunned) applies SVG auras and badges."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Valeros", "character_class": "Fighter", "max_hp": 50},
    )
    char_id = create_res.json()["character_id"]

    # 1. Apply Poisoned condition via frontdoor POST /api/v1/characters/{id}/conditions
    cond1_res = char_client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "poisoned", "duration_rounds": 5, "source": "Spider Venom"},
    )
    assert cond1_res.status_code == 200
    cond1_data = cond1_res.json()
    assert "poisoned" in cond1_data["condition_badges"]
    assert "data:image/svg+xml" in cond1_data["active_portrait_url"]

    port_res = char_client.get(f"/api/v1/characters/{char_id}/portrait")
    assert port_res.status_code == 200
    assert "poisoned-aura" in port_res.json()["svg_overlay"]
    assert "poison-bubbles" in port_res.json()["svg_overlay"]

    # 2. Apply Stunned condition
    cond2_res = char_client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "stunned", "duration_rounds": 2, "source": "Mind Blast"},
    )
    assert cond2_res.status_code == 200
    cond2_data = cond2_res.json()
    assert "stunned" in cond2_data["condition_badges"]
    assert "poisoned" in cond2_data["condition_badges"]

    port2_res = char_client.get(f"/api/v1/characters/{char_id}/portrait")
    assert "stunned-stars" in port2_res.json()["svg_overlay"]

    # 3. Remove Poisoned condition via frontdoor DELETE
    del_res = char_client.delete(f"/api/v1/characters/{char_id}/conditions/poisoned")
    assert del_res.status_code == 200
    assert "poisoned" not in del_res.json()["condition_badges"]
    assert "stunned" in del_res.json()["condition_badges"]


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


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_authorization(char_client: TestClient):
    """Verify SpiceDB Zanzibar permissions on character wardrobe and portrait mutation."""
    spicedb: SpiceDBClient = get_char_spicedb()

    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Evelyn the Sorcerer", "character_class": "Sorcerer", "max_hp": 25},
    )
    char_id = create_res.json()["character_id"]

    owner_id = f"user-{uuid4().hex[:6]}"
    stranger_id = f"stranger-{uuid4().hex[:6]}"

    # Grant edit permission strictly to owner_id
    await spicedb.write_relationship(
        resource_type="character",
        resource_id=str(char_id),
        relation="owner",
        subject_type="user",
        subject_id=owner_id,
    )

    # Stranger attempt must fail with 403 Forbidden
    res_stranger = char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"image_url": "/malicious/avatar.png"},
        headers={"X-User-Id": stranger_id},
    )
    assert res_stranger.status_code == 403
    assert (
        "Forbidden" in res_stranger.json()["detail"]
        or "permission" in res_stranger.json()["detail"]
    )

    # Owner attempt must succeed with 200 OK
    res_owner = char_client.post(
        f"/api/v1/characters/{char_id}/portrait/active",
        json={"image_url": "/sanctioned/avatar.png"},
        headers={"X-User-Id": owner_id},
    )
    assert res_owner.status_code == 200
    assert "/sanctioned/avatar.png" in res_owner.json()["base_portrait_url"]


def test_blackbox_ui_microfrontend_manifest_and_storybook(char_client: TestClient):
    """Verify <runefoble-wardrobe-gallery> microfrontend element and Storybook stories."""
    # 1. Microfrontend manifest endpoint
    manifest_res = char_client.get("/ui/manifest")
    assert manifest_res.status_code == 200
    manifest = manifest_res.json()
    assert "runefoble-wardrobe-gallery" in manifest["components"]
    assert "runefoble-wardrobe-gallery" in manifest["tags"]
    assert any("runefoble-wardrobe-gallery.styles" in s for s in manifest.get("styles", []))

    # 2. Lit Component TypeScript source & Companion Styles
    comp_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-wardrobe-gallery')" in comp_src
    assert "wardrobeGalleryStyles" in comp_src
    assert "portrait-selected" in comp_src
    assert "generate-wardrobe" in comp_src

    styles_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts"
    assert styles_file.is_file()
    styles_src = styles_file.read_text(encoding="utf-8")
    assert "wardrobeGalleryStyles" in styles_src
    assert "--rf-bg-card" in styles_src

    # 3. Storybook stories
    stories_file = (
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.stories.ts"
    )
    assert stories_file.is_file()
    stories_src = stories_file.read_text(encoding="utf-8")
    assert "HealthyBase" in stories_src
    assert "BloodiedInjury" in stories_src
    assert "PoisonedAffliction" in stories_src
    assert "GalaAttireMasquerade" in stories_src


def test_blackbox_wardrobe_gallery_styles_and_subcomponents_modular_decomposition():
    """Verify TASK-0131: Wardrobe gallery styles extracted to companion *.styles.ts module and line limits (<250 lines)."""
    comp_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts"
    styles_file = REPO_ROOT / "services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts"

    assert comp_file.is_file(), f"{comp_file} must exist"
    assert styles_file.is_file(), f"{styles_file} must exist"

    comp_lines = len(comp_file.read_text(encoding="utf-8").splitlines())
    styles_lines = len(styles_file.read_text(encoding="utf-8").splitlines())

    assert comp_lines < 250, f"Component file has {comp_lines} lines (expected < 250)"
    assert styles_lines < 250, f"Styles file has {styles_lines} lines (expected < 250)"

    comp_src = comp_file.read_text(encoding="utf-8")
    assert "renderConditionBadge" in comp_src
    assert "renderConditionBadges" in comp_src
    assert "renderVariantCard" in comp_src
    assert "renderActiveSection" in comp_src
    assert "renderForgePanel" in comp_src
