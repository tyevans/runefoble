"""Blackbox frontdoor tests for gateway character routes (TASK-0252, TASK-0585).

The gateway proxies character create, list, read and campaign assignment to character_sheet,
which owns the aggregate and the SpiceDB relations. Each test runs character_sheet and
game_session as live loopback upstreams. Setup goes through the public HTTP routes only.
Verifies:
1. Character creation records the caller as owner and the public response shape.
2. Listing returns only characters the caller may view.
3. Read returns 403 to a stranger and the owner's permission body.
4. Campaign assignment grants and revokes party view. The owner withholds the title from non-members.
5. Create stores level and portrait. A bad level or portrait returns 422.
6. Create refuses fields that character_sheet cannot store, with 422 (never a silent drop).
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app


@pytest.fixture
def client(character_sheet_upstream, game_session_upstream):
    """Enter the gateway lifespan after both upstreams serve, so the proxy reaches them."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def test_character_creation_records_the_caller_as_owner(trusted_ws_issuer, client):
    """POST creates the character in character_sheet and returns both naming styles."""
    headers = _auth(trusted_ws_issuer, "user_valeros")
    payload = {
        "name": "Valeros of Korvosa",
        "characterClass": "Fighter",
        "subclass": "Battle Master",
        "maxHp": 45,
        "armorClass": 18,
        "speed": 30,
    }

    res = client.post("/api/v1/characters", json=payload, headers=headers)

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["name"] == "Valeros of Korvosa"
    assert data["character_class"] == "Fighter"
    assert data["characterClass"] == "Fighter"
    assert data["subclass"] == "Battle Master"
    assert data["level"] == 1
    assert data["current_hp"] == 45
    assert data["currentHp"] == 45
    assert data["max_hp"] == 45
    assert data["maxHp"] == 45
    assert data["armor_class"] == 18
    assert data["armorClass"] == 18
    assert data["speed"] == 30
    assert data["owner_id"] == "user_valeros"
    assert data["ownerId"] == "user_valeros"


def test_character_listing_isolation(trusted_ws_issuer, client):
    """GET /api/v1/characters lists only characters the caller owns or may view."""
    headers_alice = _auth(trusted_ws_issuer, "user_alice")
    headers_bob = _auth(trusted_ws_issuer, "user_bob")

    char_a_id = client.post(
        "/api/v1/characters",
        json={"name": "Alice the Arcane", "characterClass": "Wizard", "maxHp": 20},
        headers=headers_alice,
    ).json()["id"]
    char_b_id = client.post(
        "/api/v1/characters",
        json={"name": "Bob the Shadow", "characterClass": "Rogue", "maxHp": 22},
        headers=headers_bob,
    ).json()["id"]

    alice_ids = [c["id"] for c in client.get("/api/v1/characters", headers=headers_alice).json()]
    bob_ids = [c["id"] for c in client.get("/api/v1/characters", headers=headers_bob).json()]

    assert char_a_id in alice_ids
    assert char_b_id not in alice_ids
    assert char_b_id in bob_ids
    assert char_a_id not in bob_ids


def test_character_detail_and_view_guard(trusted_ws_issuer, client):
    """The owner reads the sheet. A stranger gets 403 with the owner's permission body."""
    headers_alice = _auth(trusted_ws_issuer, "user_alice")
    headers_stranger = _auth(trusted_ws_issuer, "user_stranger")
    char_id = client.post(
        "/api/v1/characters",
        json={"name": "Alice Guard", "characterClass": "Paladin", "maxHp": 24},
        headers=headers_alice,
    ).json()["id"]

    res_alice = client.get(f"/api/v1/characters/{char_id}", headers=headers_alice)
    assert res_alice.status_code == 200
    assert res_alice.json()["name"] == "Alice Guard"

    res_denied = client.get(f"/api/v1/characters/{char_id}", headers=headers_stranger)
    assert res_denied.status_code == 403
    assert res_denied.json()["detail"]["error"] == "permission_denied"


def test_character_campaign_assignment_and_view_propagation(trusted_ws_issuer, client):
    """PATCH assigns the campaign, grants party view, and unassigning revokes it."""
    headers_alice = _auth(trusted_ws_issuer, "user_alice")
    headers_dm = _auth(trusted_ws_issuer, "dm_merlin")
    headers_party_member = _auth(trusted_ws_issuer, "user_grognak")
    headers_outsider = _auth(trusted_ws_issuer, "user_outsider")

    campaign_id = client.post(
        "/api/v1/campaigns",
        json={"title": "Curse of Strahd", "setting": "Barovia"},
        headers=headers_dm,
    ).json()["id"]
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=headers_dm
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=headers_party_member,
    )
    assert joined.status_code == 200, joined.text

    char_id = client.post(
        "/api/v1/characters",
        json={"name": "Alice Barovian", "characterClass": "Cleric", "maxHp": 12},
        headers=headers_alice,
    ).json()["id"]

    assert (
        client.get(f"/api/v1/characters/{char_id}", headers=headers_party_member).status_code == 403
    )
    assert (
        client.patch(
            f"/api/v1/characters/{char_id}/campaign",
            json={"campaignId": campaign_id},
            headers=headers_outsider,
        ).status_code
        == 403
    )

    res_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=headers_alice,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["campaign_id"] == campaign_id
    assert res_patch.json()["campaignId"] == campaign_id
    # Alice is not a campaign member, so the owner withholds the campaign title from her.
    assert res_patch.json()["campaignTitle"] is None

    res_member = client.get(f"/api/v1/characters/{char_id}", headers=headers_party_member)
    assert res_member.status_code == 200
    assert res_member.json()["name"] == "Alice Barovian"
    assert res_member.json()["campaignTitle"] == "Curse of Strahd"

    assert client.get(f"/api/v1/characters/{char_id}", headers=headers_outsider).status_code == 403

    res_unassign = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": None},
        headers=headers_alice,
    )
    assert res_unassign.status_code == 200
    assert res_unassign.json()["campaign_id"] is None
    assert (
        client.get(f"/api/v1/characters/{char_id}", headers=headers_party_member).status_code == 403
    )


def test_create_stores_level_and_portrait_and_read_returns_them(trusted_ws_issuer, client):
    """Level and portrait set at creation come back on create and on read (TASK-0905)."""
    headers = _auth(trusted_ws_issuer, "user_valeros")
    portrait = (
        "data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%2F%3E"
    )
    payload = {
        "name": "Valeros",
        "characterClass": "Fighter",
        "level": 4,
        "maxHp": 45,
        "portraitUrl": portrait,
    }

    res = client.post("/api/v1/characters", json=payload, headers=headers)

    assert res.status_code == 201, res.text
    assert res.json()["level"] == 4
    assert res.json()["portraitUrl"] == portrait
    read = client.get(f"/api/v1/characters/{res.json()['id']}", headers=headers)
    assert read.status_code == 200
    assert read.json()["level"] == 4
    assert read.json()["portrait_url"] == portrait


@pytest.mark.parametrize("level", [0, 21])
def test_create_refuses_a_level_outside_one_to_twenty(trusted_ws_issuer, client, level):
    headers = _auth(trusted_ws_issuer, "user_valeros")
    body = {"name": "Odd", "characterClass": "Fighter", "level": level, "maxHp": 10}
    assert client.post("/api/v1/characters", json=body, headers=headers).status_code == 422


def test_create_refuses_a_portrait_that_is_not_a_url_or_asset_reference(trusted_ws_issuer, client):
    """character_sheet refuses the portrait and the gateway passes the 422 on."""
    headers = _auth(trusted_ws_issuer, "user_valeros")
    body = {"name": "Odd", "characterClass": "Fighter", "portraitUrl": "javascript:alert(1)"}
    assert client.post("/api/v1/characters", json=body, headers=headers).status_code == 422


def test_create_refuses_fields_character_sheet_cannot_store(trusted_ws_issuer, client):
    """A starting HP or a stand-in flag that character_sheet cannot keep returns 422, not a drop."""
    headers = _auth(trusted_ws_issuer, "user_valeros")
    body = {
        "name": "Too Hurt",
        "characterClass": "Fighter",
        "maxHp": 45,
        "currentHp": 20,
        "isAiStandIn": True,
    }

    res = client.post("/api/v1/characters", json=body, headers=headers)

    assert res.status_code == 422
    assert res.json()["detail"]["fields"] == ["currentHp", "isAiStandIn"]


def test_character_without_portrait_answers_null_portrait_url(trusted_ws_issuer, client):
    """A character created with no portrait answers `portrait_url: null`, never a missing file."""
    headers = _auth(trusted_ws_issuer, "user_portraitless")
    payload = {"name": "Nameless Face", "characterClass": "Rogue", "maxHp": 18}

    res = client.post("/api/v1/characters", json=payload, headers=headers)

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["portrait_url"] is None
    assert data["portraitUrl"] is None

    read = client.get(f"/api/v1/characters/{data['id']}", headers=headers)
    assert read.status_code == 200
    assert read.json()["portrait_url"] is None
