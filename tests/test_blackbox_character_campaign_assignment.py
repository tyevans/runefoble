"""Blackbox tests verifying CharacterAggregate campaign assignment and core attributes.

Complies strictly with:
- ADR-0002: Domain Events via eventsource-py
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 2: Domain state transitions flow strictly through DeclarativeAggregate subclasses
- Hard Invariant 6: File length < 500 lines
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

import pytest
from character_sheet.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer


@pytest.fixture
def client(spicedb):
    return TestClient(app, headers=bearer("character-owner"))


def test_blackbox_character_creation_with_core_attributes(client):
    """Verify frontdoor character creation with core 5e attributes and campaign_id."""
    scores = {"str": 18, "dex": 12, "con": 16, "int": 8, "wis": 10, "cha": 14}
    payload = {
        "name": "Minsc",
        "character_class": "Ranger",
        "max_hp": 52,
        "player_id": "usr-minsc",
        "personality_traits": ["righteous", "hamster-loving"],
        "campaign_id": "camp-rashemen-44",
        "subclass": "Hunter",
        "armor_class": 16,
        "speed_ft": 30,
        "ability_scores": scores,
    }

    create_res = client.post("/api/v1/characters", json=payload)
    assert create_res.status_code == 200
    data = create_res.json()
    char_id = data["character_id"]

    assert data["name"] == "Minsc"
    assert data["campaign_id"] == "camp-rashemen-44"
    assert data["subclass"] == "Hunter"
    assert data["armor_class"] == 16
    assert data["speed_ft"] == 30
    assert data["ability_scores"] == scores

    # GET character through public frontdoor query
    get_res = client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["character_id"] == char_id
    assert fetched["campaign_id"] == "camp-rashemen-44"
    assert fetched["subclass"] == "Hunter"
    assert fetched["armor_class"] == 16
    assert fetched["speed_ft"] == 30
    assert fetched["ability_scores"] == scores


def test_blackbox_character_campaign_assignment_patch(client):
    """Verify PATCH /api/v1/characters/{character_id}/campaign lifecycle."""
    # 1. Create character without campaign
    create_res = client.post(
        "/api/v1/characters",
        json={"name": "Shadowheart", "character_class": "Cleric", "max_hp": 32},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]
    assert create_res.json()["campaign_id"] is None
    assert create_res.json()["subclass"] is None
    assert create_res.json()["armor_class"] == 10
    assert create_res.json()["speed_ft"] == 30
    assert create_res.json()["ability_scores"] == {
        "str": 10,
        "dex": 10,
        "con": 10,
        "int": 10,
        "wis": 10,
        "cha": 10,
    }

    # 2. Assign character to campaign
    patch_res = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-shar-cloister", "assigned_by": "dm-viconia"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["campaign_id"] == "camp-shar-cloister"

    # Verify query reflects assigned campaign
    get_res1 = client.get(f"/api/v1/characters/{char_id}")
    assert get_res1.status_code == 200
    assert get_res1.json()["campaign_id"] == "camp-shar-cloister"

    # 3. Re-assign to a different campaign
    patch_res2 = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-selune-temple", "assigned_by": "dm-isobel"},
    )
    assert patch_res2.status_code == 200
    assert patch_res2.json()["campaign_id"] == "camp-selune-temple"

    # 4. Unassign character from campaign (campaign_id: null)
    unassign_res = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": None, "assigned_by": "player-shadowheart"},
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["campaign_id"] is None

    # Verify query reflects unassigned status
    get_res2 = client.get(f"/api/v1/characters/{char_id}")
    assert get_res2.status_code == 200
    assert get_res2.json()["campaign_id"] is None


@pytest.mark.asyncio
async def test_blackbox_campaign_assignment_spicedb_authorization(client, spicedb):
    """Verify SpiceDB Zanzibar permissions on campaign assignment endpoint."""
    owner_user = "usr-owner-001"
    unauthorized_user = "usr-stranger-999"

    # Create character owned by owner_user
    create_res = client.post(
        "/api/v1/characters",
        json={
            "name": "Astarion",
            "character_class": "Rogue",
            "max_hp": 28,
            "player_id": owner_user,
        },
        headers=bearer(owner_user),
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    # Write explicit owner relation in mock SpiceDB
    await spicedb.write_relationship("character", char_id, "owner", "user", owner_user)

    # Attempt to assign campaign as unauthorized user -> 403 Forbidden
    unauth_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-cazador"},
        headers=bearer(unauthorized_user),
    )
    assert unauth_patch.status_code == 403
    assert unauth_patch.json()["detail"]["error"] == "permission_denied"

    # Authorized user (owner) can assign campaign -> 200 OK
    auth_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-cazador"},
        headers=bearer(owner_user),
    )
    assert auth_patch.status_code == 200
    assert auth_patch.json()["campaign_id"] == "camp-cazador"

    # Verify SpiceDB relationship was written
    rels = await spicedb.read_relationships(
        resource_type="character", resource_id=char_id, relation="campaign"
    )
    assert any(r.subject_id == "camp-cazador" for r in rels)

    # Authorized user unassigns campaign
    unassign_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": None},
        headers=bearer(owner_user),
    )
    assert unassign_patch.status_code == 200
    assert unassign_patch.json()["campaign_id"] is None

    # Verify SpiceDB campaign relationship was deleted
    rels_after = await spicedb.read_relationships(
        resource_type="character", resource_id=char_id, relation="campaign"
    )
    assert len(rels_after) == 0
