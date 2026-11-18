"""Blackbox tests: gateway character routes hold no state and forward to character_sheet (TASK-0585).

Each test drives the public HTTP routes. character_sheet runs as a live loopback upstream.
Verifies that a character survives a gateway restart, that an unreachable owner returns 503,
and that a character is listed only for the users who may view it.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def test_created_character_survives_a_gateway_restart(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """Build the gateway app twice over the same owner. The second instance still lists it."""
    headers = _auth(trusted_ws_issuer, "user_restart")

    with TestClient(app) as first:
        char_id = first.post(
            "/api/v1/characters",
            json={"name": "Durable", "characterClass": "Monk"},
            headers=headers,
        ).json()["id"]

    with TestClient(app) as second:
        listed = second.get("/api/v1/characters", headers=headers)
        assert listed.status_code == 200
        assert char_id in [c["id"] for c in listed.json()]


def test_character_owned_by_another_user_is_not_listed(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """A stranger's character does not appear in the caller's list."""
    with TestClient(app) as client:
        owner_char = client.post(
            "/api/v1/characters",
            json={"name": "Private", "characterClass": "Bard"},
            headers=_auth(trusted_ws_issuer, "user_owner"),
        ).json()["id"]

        stranger_ids = [
            c["id"]
            for c in client.get(
                "/api/v1/characters", headers=_auth(trusted_ws_issuer, "user_other")
            ).json()
        ]

    assert owner_char not in stranger_ids


def test_campaign_filter_is_applied_by_character_sheet(
    trusted_ws_issuer, character_sheet_upstream, game_session_upstream
):
    """GET /api/v1/characters?campaignId= returns only the characters assigned to that campaign."""
    headers = _auth(trusted_ws_issuer, "user_filter")
    with TestClient(app) as client:
        assigned = client.post(
            "/api/v1/characters",
            json={"name": "Assigned", "characterClass": "Ranger"},
            headers=headers,
        ).json()["id"]
        unassigned = client.post(
            "/api/v1/characters",
            json={"name": "Loose", "characterClass": "Ranger"},
            headers=headers,
        ).json()["id"]
        campaign = "00000000-0000-4000-8000-000000000042"
        patched = client.patch(
            f"/api/v1/characters/{assigned}/campaign",
            json={"campaignId": campaign},
            headers=headers,
        )
        assert patched.status_code == 200, patched.text

        ids = [
            c["id"]
            for c in client.get(
                "/api/v1/characters", params={"campaignId": campaign}, headers=headers
            ).json()
        ]

    assert assigned in ids
    assert unassigned not in ids


def test_owner_down_returns_503_on_create(trusted_ws_issuer, monkeypatch):
    """With character_sheet unreachable, create fails with 503. It never answers from memory."""
    monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", "http://127.0.0.1:9")
    headers = _auth(trusted_ws_issuer, "user_down")

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/characters",
            json={"name": "Ghost", "characterClass": "Fighter"},
            headers=headers,
        )

    assert res.status_code == 503


@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_bearer_is_refused_at_the_gateway(
    method, character_sheet_upstream, game_session_upstream
):
    """A request without a verified bearer token gets 401 before any upstream call."""
    with TestClient(app) as client:
        if method == "get":
            res = client.get("/api/v1/characters")
        else:
            res = client.post(
                "/api/v1/characters", json={"name": "Anon", "characterClass": "Fighter"}
            )
    assert res.status_code == 401
