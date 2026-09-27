"""Blackbox TDD tests for Collaborative Campaign World Atlas & Living Party Codex.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public HTTP endpoints
using TestClient(app) from campaign_lore.main and verify observable state projections
and SpiceDB Zanzibar access control.
"""

from uuid import UUID, uuid4

import pytest
from campaign_lore.dependencies import (
    get_atlas_repo,
    get_codex_repo,
    get_retrieval_engine,
    get_spicedb_client,
)
from campaign_lore.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_blackbox_atlas_pin_placement_and_territory_containment(client: TestClient):
    """Test public frontdoor territory boundary definition, pin placement, and coordinate containment."""
    spicedb = get_spicedb_client()
    campaign_id = str(uuid4())
    user_id = "rowan_chronicler"

    # Grant rowan view access to campaign
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )

    # 1. Define geopolitical territory boundary polygon (Silverkeep Realm)
    territory_payload = {
        "name": "Silverkeep Garrison",
        "layer": "continental",
        "polygon_coordinates": [
            [100.0, 100.0],
            [300.0, 100.0],
            [300.0, 300.0],
            [100.0, 300.0],
        ],
        "owner_faction": "Silverguard Alliance",
        "is_contested": True,
        "era": "Session 12: Liberation",
        "metadata": {"banner_color": "#4361ee"},
    }
    terr_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/territories",
        json=territory_payload,
        headers={"x-user-id": user_id},
    )
    assert terr_resp.status_code == 201, terr_resp.text
    terr_data = terr_resp.json()
    assert terr_data["name"] == "Silverkeep Garrison"
    assert terr_data["is_contested"] is True
    territory_id = terr_data["territory_id"]

    # 2. Place milestone pin inside the territory coordinates (200.0, 200.0)
    pin_payload = {
        "title": "Silverkeep Garrison Liberation",
        "coordinates": {"x": 200.0, "y": 200.0},
        "layer": "continental",
        "description": "Party liberated the garrison from the shadow legion.",
        "era": "Session 12: Liberation",
        "session_id": "session-12",
        "linked_entity_ids": ["entity-silverguard"],
        "metadata": {"icon": "castle_flag"},
    }
    pin_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins",
        json=pin_payload,
        headers={"x-user-id": user_id},
    )
    assert pin_resp.status_code == 201, pin_resp.text
    pin_data = pin_resp.json()
    assert pin_data["title"] == "Silverkeep Garrison Liberation"
    assert "pin_id" in pin_data
    pin_id = pin_data["pin_id"]

    # Verify territory was automatically identified through point-in-polygon containment
    assert pin_data["metadata"]["territory_id"] == territory_id
    assert pin_data["metadata"]["territory_name"] == "Silverkeep Garrison"
    assert "normalized_coordinates" in pin_data["metadata"]

    # Verify event sourcing persistence
    atlas_repo = get_atlas_repo()
    aggregate = await atlas_repo.load(UUID(campaign_id))
    assert len(aggregate.state.pins) == 1
    assert aggregate.state.pins[0]["pin_id"] == pin_id
    assert len(aggregate.state.territories) == 1

    # 3. Retrieve single pin via frontdoor GET
    get_pin_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins/{pin_id}",
        headers={"x-user-id": user_id},
    )
    assert get_pin_resp.status_code == 200
    assert get_pin_resp.json()["title"] == "Silverkeep Garrison Liberation"


@pytest.mark.asyncio
async def test_blackbox_atlas_deep_zoom_and_chronological_filtering(client: TestClient):
    """Test deep-zoom layer projection, contested zone detection, and chronological era filtering."""
    spicedb = get_spicedb_client()
    campaign_id = str(uuid4())
    user_id = "rowan_chronicler"

    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )

    # Place Pin in Era 1
    client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins",
        json={
            "title": "Ancient Sunken Ruins",
            "coordinates": {"x": 50.0, "y": 80.0},
            "layer": "continental",
            "era": "Age of Ash",
            "session_id": "session-1",
        },
        headers={"x-user-id": user_id},
    )

    # Place Pin in Era 2
    client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins",
        json={
            "title": "Citadel of the Dawn",
            "coordinates": {"x": 450.0, "y": 600.0},
            "layer": "continental",
            "era": "Age of Rebirth",
            "session_id": "session-20",
        },
        headers={"x-user-id": user_id},
    )

    # Define a contested boundary territory
    client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/territories",
        json={
            "name": "Obsidian Borderlands",
            "layer": "continental",
            "polygon_coordinates": [[400.0, 500.0], [600.0, 500.0], [500.0, 700.0]],
            "owner_faction": "Disputed",
            "is_contested": True,
            "era": "Age of Rebirth",
        },
        headers={"x-user-id": user_id},
    )

    # 1. Query full atlas without era filter
    full_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas?layer=continental",
        headers={"x-user-id": user_id},
    )
    assert full_resp.status_code == 200
    full_data = full_resp.json()
    assert len(full_data["pins"]) == 2
    assert len(full_data["contested_zones"]) == 1
    assert full_data["contested_zones"][0]["name"] == "Obsidian Borderlands"
    assert full_data["layer_extent"] == 1000.0

    # 2. Query atlas filtered by era "Age of Ash"
    ash_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas?layer=continental&era=Age of Ash",
        headers={"x-user-id": user_id},
    )
    assert ash_resp.status_code == 200
    ash_data = ash_resp.json()
    assert len(ash_data["pins"]) == 1
    assert ash_data["pins"][0]["title"] == "Ancient Sunken Ruins"
    # Age of Rebirth territory is filtered out
    assert len(ash_data["territories"]) == 0
    assert len(ash_data["contested_zones"]) == 0

    # 3. Query atlas filtered by session "session-20"
    sess_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas?layer=continental&session_id=session-20",
        headers={"x-user-id": user_id},
    )
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert len(sess_data["pins"]) == 1
    assert sess_data["pins"][0]["title"] == "Citadel of the Dawn"

    # 4. Toggle layer visibility
    toggle_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/layers/toggle",
        json={"layer": "municipal", "is_visible": False},
        headers={"x-user-id": user_id},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_visible"] is False


@pytest.mark.asyncio
async def test_blackbox_collaborative_codex_with_spicedb_zanzibar_privacy(
    client: TestClient,
):
    """Test codex publishing, automatic redstring hyperlinking, and SpiceDB Zanzibar private vs shared access."""
    spicedb = get_spicedb_client()
    campaign_id = str(uuid4())
    rowan_id = "rowan_chronicler"
    bob_player_id = "bob_player"

    # Seed redstring graph with known campaign entity "Order of the Obsidian Veil"
    retrieval_engine = get_retrieval_engine()
    await retrieval_engine.ingest_document(
        document_id=uuid4(),
        campaign_id=UUID(campaign_id),
        title="Arcane Factions Overview",
        content="The Order of the Obsidian Veil is a secretive cabal of warlocks.",
        is_secret=False,
    )

    # Configure Rowan and Bob in Zanzibar
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=rowan_id,
    )
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=bob_player_id,
    )

    # 1. Rowan creates a PRIVATE codex entry containing entity mentions
    private_entry_payload = {
        "title": "Secret Hypothesis on the Cabal",
        "content": "I suspect the Order of the Obsidian Veil is tunneling into Silverkeep Garrison.",
        "privacy": "private",
        "era": "Session 12",
        "tags": ["theory", "veil"],
    }
    create_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        json=private_entry_payload,
        headers={"x-user-id": rowan_id},
    )
    assert create_resp.status_code == 201, create_resp.text
    entry_data = create_resp.json()
    entry_id = entry_data["entry_id"]
    assert entry_data["privacy"] == "private"
    assert entry_data["author_id"] == rowan_id

    # Verify automatic entity hyperlinking against redstring graph
    assert len(entry_data["linked_entities"]) >= 1
    assert any("Order of the Obsidian Veil" in e["name"] for e in entry_data["linked_entities"])
    assert "Order of the Obsidian Veil](#lore/entity/" in entry_data["illuminated_content"]

    # Verify event sourcing persistence
    codex_repo = get_codex_repo()
    aggregate = await codex_repo.load(UUID(entry_id))
    assert aggregate.state.title == "Secret Hypothesis on the Cabal"
    assert aggregate.state.privacy == "private"

    # 2. Rowan (author) can read the private entry
    rowan_get = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        headers={"x-user-id": rowan_id},
    )
    assert rowan_get.status_code == 200
    assert rowan_get.json()["title"] == "Secret Hypothesis on the Cabal"

    # 3. Bob (party player) CANNOT read Rowan's private entry (Zanzibar 403 Forbidden)
    bob_get = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        headers={"x-user-id": bob_player_id},
    )
    assert bob_get.status_code == 403
    assert "denies access to this private codex entry" in bob_get.json()["detail"]

    # Bob's listing of codex entries excludes Rowan's private note
    bob_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        headers={"x-user-id": bob_player_id},
    )
    assert bob_list.status_code == 200
    assert not any(e["entry_id"] == entry_id for e in bob_list.json())

    # Rowan's listing includes her own private note
    rowan_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        headers={"x-user-id": rowan_id},
    )
    assert rowan_list.status_code == 200
    assert any(e["entry_id"] == entry_id for e in rowan_list.json())

    # 4. Rowan shares the entry with the party ("party_shared")
    patch_resp = client.patch(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        json={"privacy": "party_shared"},
        headers={"x-user-id": rowan_id},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["privacy"] == "party_shared"

    # 5. Now Bob (campaign player) CAN read the illuminated shared entry!
    bob_get_shared = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries/{entry_id}",
        headers={"x-user-id": bob_player_id},
    )
    assert bob_get_shared.status_code == 200
    assert bob_get_shared.json()["privacy"] == "party_shared"
    assert (
        "Order of the Obsidian Veil](#lore/entity/" in bob_get_shared.json()["illuminated_content"]
    )

    # Bob's listing now includes the entry
    bob_list_shared = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        headers={"x-user-id": bob_player_id},
    )
    assert any(e["entry_id"] == entry_id for e in bob_list_shared.json())


def test_blackbox_ui_manifest_advertises_atlas(client: TestClient):
    """Test that /ui/manifest advertises runefoble-campaign-atlas."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "campaign_lore"
    assert "runefoble-campaign-atlas" in data["components"]
    assert "runefoble-campaign-codex" in data["components"]
