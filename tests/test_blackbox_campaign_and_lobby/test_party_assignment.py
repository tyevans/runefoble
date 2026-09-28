"""Blackbox frontdoor tests for Character Roster and Campaign Party Assignment (US-0064).

Governed by ADR-0001, ADR-0003, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client


@pytest.mark.asyncio
async def test_character_creation_and_party_assignment(
    client_gw: TestClient, client_char: TestClient
):
    """Verify character creation, SpiceDB ownership, and campaign party binding."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}
    spicedb = get_spicedb_client()

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Tomb of the Star-Eater"}, headers=headers_dm
    )
    camp_id = camp_res.json()["id"]

    # 1. Marcus creates character "Valeros" via POST /api/v1/characters
    char_res = client_char.post(
        "/api/v1/characters",
        json={
            "name": "Valeros",
            "character_class": "Fighter",
            "max_hp": 45,
            "player_id": "player_marcus",
        },
        headers=headers_marcus,
    )
    assert char_res.status_code == 200
    char_data = char_res.json()
    char_id = str(char_data.get("character_id") or char_data["id"])
    assert char_data["name"] == "Valeros"
    assert char_data["max_hp"] == 45

    # 2. Verify Marcus holds owner and edit permission for the character
    assert await spicedb.check_permission("character", char_id, "edit", "user", "player_marcus")

    # 3. Marcus assigns character to campaign party via frontdoor sync API
    sync_res = client_gw.post(
        "/api/v1/auth/sync/character-ownership",
        json={"character_id": char_id, "user_id": "player_marcus", "campaign_id": camp_id},
        headers=headers_marcus,
    )
    assert sync_res.status_code == 200
    assert sync_res.json()["status"] == "ownership_bound"

    # 4. DM Evelyn now has edit & view on character via Zanzibar campaign->run_session
    assert await spicedb.check_permission("character", char_id, "edit", "user", "dm_evelyn")
    assert await spicedb.check_permission("character", char_id, "view", "user", "dm_evelyn")

    # 5. Unrelated stranger has no edit permission
    assert not await spicedb.check_permission("character", char_id, "edit", "user", "stranger_bob")


@pytest.mark.asyncio
async def test_party_roster_assignment_capacity(client_gw: TestClient, client_char: TestClient):
    """Verify multiple characters can be bound to the party roster up to active limits."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    spicedb = get_spicedb_client()

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Roster Quest"}, headers=headers_dm
    )
    camp_id = camp_res.json()["id"]

    for idx, name in enumerate(["Valeros", "Kyra", "Merisiel", "Ezren"]):
        char_res = client_char.post(
            "/api/v1/characters",
            json={"name": name, "character_class": "Hero", "max_hp": 30, "player_id": f"p_{idx}"},
        )
        assert char_res.status_code == 200
        cid = str(char_res.json().get("character_id") or char_res.json()["id"])
        sync_res = client_gw.post(
            "/api/v1/auth/sync/character-ownership",
            json={"character_id": cid, "user_id": f"p_{idx}", "campaign_id": camp_id},
        )
        assert sync_res.status_code == 200
        assert await spicedb.check_permission("character", cid, "view", "user", "dm_evelyn")
