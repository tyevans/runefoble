"""Blackbox TDD tests for Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public HTTP endpoints
using TestClient(app) from campaign_lore.main and verify emitted CloudEvents.
"""

from uuid import UUID, uuid4

import pytest
from campaign_lore.dependencies import get_handout_repo, get_relic_repo, get_spicedb_client
from campaign_lore.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_blackbox_handout_generation_and_seal_cracking(client: TestClient):
    """Test public frontdoor generation of diegetic sealed handouts, breaking seal with audio."""
    campaign_id = str(uuid4())

    # 1. Frontdoor handout generation
    gen_payload = {
        "campaign_id": campaign_id,
        "title": "Intercepted Courier Scroll",
        "content": "To the Black Gate Vanguard: The Citadel guards rotate at midnight.",
        "handout_type": "letter",
        "paper_texture": "weathered_parchment",
        "calligraphy_font": "royal_chancery",
        "seal_color": "crimson",
        "seal_stamp": "raven_crest",
        "has_wax_seal": True,
        "secret_ink_text": "THE HIGH PRIEST IS AN ILLUSION",
    }
    resp = client.post("/api/v1/lore/handouts/generate", json=gen_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "handout_id" in data
    handout_id = data["handout_id"]
    assert data["campaign_id"] == campaign_id
    assert data["title"] == "Intercepted Courier Scroll"
    assert data["status"] == "forged"
    assert data["has_wax_seal"] is True
    assert data["wax_seal"]["state"] == "intact"
    assert data["wax_seal"]["color"] == "crimson"
    assert data["wax_seal"]["stamp_symbol"] == "raven_crest"
    assert data["has_invisible_ink"] is True
    assert data["invisible_ink"]["secret_text"] == "THE HIGH PRIEST IS AN ILLUSION"

    # Verify event sourcing persistence
    repo = get_handout_repo()
    aggregate = await repo.load(UUID(handout_id))
    assert aggregate.state.title == "Intercepted Courier Scroll"
    assert aggregate.state.wax_seal["state"] == "intact"

    # 2. Public GET frontdoor inspection
    get_resp = client.get(f"/api/v1/lore/handouts/{handout_id}")
    assert get_resp.status_code == 200
    handout_state = get_resp.json()
    assert handout_state["handout_id"] == handout_id
    assert handout_state["wax_seal"]["state"] == "intact"

    # 3. Public frontdoor: Crack wax seal
    break_resp = client.post(
        f"/api/v1/lore/handouts/{handout_id}/break-seal",
        json={"broken_by": "valeros_player", "break_force": 14.0},
    )
    assert break_resp.status_code == 200, break_resp.text
    break_data = break_resp.json()
    assert break_data["seal_state"] == "broken"
    assert break_data["broken_by"] == "valeros_player"
    assert break_data["haptic_audio_effect"] == "wax_crack_crisp_01.wav"
    assert "Citadel guards rotate" in break_data["revealed_content"]

    # Verify aggregate state reflects broken seal
    reloaded = await repo.load(UUID(handout_id))
    assert reloaded.state.wax_seal["state"] == "broken"

    # 4. Attempting to break an already broken seal fails with 409 Conflict
    dup_resp = client.post(
        f"/api/v1/lore/handouts/{handout_id}/break-seal",
        json={"broken_by": "valeros_player"},
    )
    assert dup_resp.status_code == 409

    # 5. Public frontdoor: Reveal invisible ink under UV torchlight
    uv_resp = client.post(
        f"/api/v1/lore/handouts/{handout_id}/reveal-invisible-ink",
        json={"revealed_by": "rowan_chronicler", "uv_intensity": 1.0},
    )
    assert uv_resp.status_code == 200, uv_resp.text
    uv_data = uv_resp.json()
    assert uv_data["revealed"] is True
    assert uv_data["secret_text"] == "THE HIGH PRIEST IS AN ILLUSION"
    assert uv_data["luminescence_color"] == "#00ffcc"


@pytest.mark.asyncio
async def test_blackbox_relic_forge_and_inspection(client: TestClient):
    """Test public frontdoor 3D relic forging, WebGL mesh generation, inspection and rune deciphering."""
    campaign_id = str(uuid4())

    # 1. Frontdoor forge 3D relic
    forge_payload = {
        "campaign_id": campaign_id,
        "name": "Amulet of the Sunken Spire",
        "relic_type": "amulet",
        "model_geometry": "amulet_sunken_spire",
        "shader_properties": {
            "metallic": 0.90,
            "roughness": 0.20,
            "emissive_color": "#00ffcc",
            "emissive_intensity": 1.5,
        },
        "runes": [
            {
                "id": "rune-spire-1",
                "inscription": "Khar-Drak-Mor",
                "position": [0.0, 0.35, -0.15],
                "translated": "By Blood Sealed",
            }
        ],
    }
    forge_resp = client.post("/api/v1/lore/relics/forge", json=forge_payload)
    assert forge_resp.status_code == 200, forge_resp.text
    relic_data = forge_resp.json()

    assert "relic_id" in relic_data
    relic_id = relic_data["relic_id"]
    assert relic_data["name"] == "Amulet of the Sunken Spire"
    assert relic_data["model_geometry"] == "amulet_sunken_spire"
    assert relic_data["shader_properties"]["metallic"] == 0.90
    assert "mesh_data" in relic_data
    assert relic_data["mesh_data"]["vertex_count"] > 0
    assert len(relic_data["runes"]) == 1

    # Verify event sourcing aggregate
    relic_repo = get_relic_repo()
    relic_agg = await relic_repo.load(UUID(relic_id))
    assert relic_agg.state.name == "Amulet of the Sunken Spire"

    # 2. Public GET frontdoor relic lookup
    get_resp = client.get(f"/api/v1/lore/relics/{relic_id}")
    assert get_resp.status_code == 200
    lookup = get_resp.json()
    assert lookup["relic_id"] == relic_id
    assert lookup["shader_properties"]["emissive_color"] == "#00ffcc"

    # 3. Public frontdoor: Perform 3D inspection
    inspect_resp = client.post(
        f"/api/v1/lore/relics/{relic_id}/inspect",
        json={
            "inspected_by": "rowan_chronicler",
            "notes": "Rotating back casing reveals etched draconic glyphs.",
        },
    )
    assert inspect_resp.status_code == 200, inspect_resp.text
    inspect_data = inspect_resp.json()
    assert inspect_data["status"] == "inspected"
    assert len(inspect_data["discovered_runes"]) >= 1

    # 4. Public frontdoor: Translate etched rune
    trans_resp = client.post(
        f"/api/v1/lore/relics/{relic_id}/translate-rune",
        json={
            "rune_id": "rune-spire-1",
            "translated_by": "rowan_chronicler",
            "translation": "By Blood Sealed",
        },
    )
    assert trans_resp.status_code == 200, trans_resp.text
    trans_data = trans_resp.json()
    assert trans_data["rune_id"] == "rune-spire-1"
    assert trans_data["translation"] == "By Blood Sealed"
    assert trans_data["original_inscription"] == "Khar-Drak-Mor"


@pytest.mark.asyncio
async def test_blackbox_spicedb_authorization_enforcement(client: TestClient):
    """Test SpiceDB Zanzibar authorization checks for secret DM relics."""
    spicedb = get_spicedb_client()
    campaign_id = str(uuid4())
    user_id = f"player-{uuid4().hex[:6]}"

    # Configure user with view permission on campaign
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )

    # Forge a secret DM-only relic
    forge_resp = client.post(
        "/api/v1/lore/relics/forge",
        json={
            "campaign_id": campaign_id,
            "name": "Secret Crown of the Lich King",
            "relic_type": "chalice",
            "is_secret": True,
        },
    )
    assert forge_resp.status_code == 200
    relic_id = forge_resp.json()["relic_id"]

    # Player with only 'player' relation cannot view secret DM lore (requires run_session)
    player_resp = client.get(
        f"/api/v1/lore/relics/{relic_id}",
        headers={"x-user-id": user_id},
    )
    assert player_resp.status_code == 403

    # Promote DM user with dungeon_master relation
    dm_user = f"dm-{uuid4().hex[:6]}"
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )

    # DM can view secret relic
    dm_resp = client.get(
        f"/api/v1/lore/relics/{relic_id}",
        headers={"x-user-id": dm_user},
    )
    assert dm_resp.status_code == 200
    assert dm_resp.json()["name"] == "Secret Crown of the Lich King"


def test_blackbox_ui_manifest_discovery(client: TestClient):
    """Test that /ui/manifest advertises handout viewer and relic inspector microfrontends."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "campaign_lore"
    assert data["package"] == "@runefoble/campaign-lore-ui"
    assert "runefoble-handout-viewer" in data["components"]
    assert "runefoble-relic-inspector" in data["components"]
