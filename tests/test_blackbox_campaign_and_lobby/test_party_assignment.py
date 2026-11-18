"""Blackbox frontdoor tests for Character Roster and Campaign Party Assignment (US-0064).

Governed by ADR-0001, ADR-0003, and Hard Invariants 6 and 7.
Setup runs through the gateway public routes with signed bearer tokens:
the player creates the character (ownership), then assigns it to the campaign.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.mark.asyncio
async def test_character_creation_and_party_assignment(client_gw: TestClient, trusted_ws_issuer):
    """Verify character creation, SpiceDB ownership, and campaign party binding."""
    headers_dm = _auth(trusted_ws_issuer, "dm_evelyn")
    headers_marcus = _auth(trusted_ws_issuer, "player_marcus")
    spicedb = get_spicedb_client()

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Tomb of the Star-Eater"}, headers=headers_dm
    )
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    # 1. Marcus creates character "Valeros" via the public frontdoor
    char_res = client_gw.post(
        "/api/v1/characters",
        json={"name": "Valeros", "characterClass": "Fighter", "maxHp": 45},
        headers=headers_marcus,
    )
    assert char_res.status_code == 201
    char_data = char_res.json()
    char_id = char_data["id"]
    assert char_data["name"] == "Valeros"
    assert char_data["maxHp"] == 45

    # 2. Verify Marcus holds owner and edit permission for the character
    assert await spicedb.check_permission("character", char_id, "edit", "user", "player_marcus")

    # 3. Marcus assigns the character to the campaign party
    assign_res = client_gw.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": camp_id},
        headers=headers_marcus,
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["campaignId"] == camp_id

    # 4. DM Evelyn now has edit & view on character via Zanzibar campaign->run_session
    assert await spicedb.check_permission("character", char_id, "edit", "user", "dm_evelyn")
    assert await spicedb.check_permission("character", char_id, "view", "user", "dm_evelyn")

    # 5. Unrelated stranger has no edit permission
    assert not await spicedb.check_permission("character", char_id, "edit", "user", "stranger_bob")


@pytest.mark.asyncio
async def test_party_roster_assignment_capacity(client_gw: TestClient, trusted_ws_issuer):
    """Verify multiple characters can be bound to the party roster up to active limits."""
    headers_dm = _auth(trusted_ws_issuer, "dm_evelyn")
    spicedb = get_spicedb_client()

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Roster Quest"}, headers=headers_dm
    )
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["id"]

    for idx, name in enumerate(["Valeros", "Kyra", "Merisiel", "Ezren"]):
        player_id = f"p_{idx}"
        headers_player = _auth(trusted_ws_issuer, player_id)
        char_res = client_gw.post(
            "/api/v1/characters",
            json={"name": name, "characterClass": "Hero", "maxHp": 30},
            headers=headers_player,
        )
        assert char_res.status_code == 201
        cid = char_res.json()["id"]
        assign_res = client_gw.patch(
            f"/api/v1/characters/{cid}/campaign",
            json={"campaignId": camp_id},
            headers=headers_player,
        )
        assert assign_res.status_code == 200
        assert await spicedb.check_permission("character", cid, "view", "user", "dm_evelyn")
