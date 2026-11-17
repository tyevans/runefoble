"""Tests for Gateway API Zanzibar object-level authorization.

Setup runs through public frontdoors only. The owner creates a campaign, and
members redeem invite tokens. No test writes SpiceDB tuples directly (ADR-0015 a, d).
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

client = TestClient(app)


def _bearer(issuer: SigningTestIssuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_campaign_with_session(owner_headers: dict[str, str]) -> tuple[str, str]:
    """Create a campaign as the owner and return (campaign_id, first_session_id)."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Zanzibar Authorization Campaign"},
        headers=owner_headers,
    )
    assert res.status_code == 201
    campaign_id = res.json()["id"]

    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=owner_headers)
    assert sessions.status_code == 200
    return campaign_id, sessions.json()[0]["id"]


def _join_with_invite(
    campaign_id: str,
    owner_headers: dict[str, str],
    member_headers: dict[str, str],
    role: str,
) -> None:
    """Owner creates an invite for `role`; the member redeems it."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=owner_headers,
    )
    assert invite.status_code == 201
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=member_headers,
    )
    assert joined.status_code == 200


@pytest.mark.asyncio
async def test_zanzibar_authorization_enforcement(signing_issuer):
    """Verify that Gateway API enforces SpiceDB Zanzibar permissions without hardcoded role checks."""
    owner = _bearer(signing_issuer, "owner_dana")
    player = _bearer(signing_issuer, "player_alice")
    stranger = _bearer(signing_issuer, "stranger_bob")
    campaign_id, session_id = _create_campaign_with_session(owner)

    # 1. Unassigned user tries to view session -> 403 Forbidden
    res_unauth = client.get(f"/api/v1/sessions/{session_id}", headers=stranger)
    assert res_unauth.status_code == 403
    err_data = res_unauth.json()["detail"]
    assert err_data["error"] == "permission_denied"
    assert err_data["required_permission"] == "view"

    # 2. Owner invites the player; the player redeems the invite
    _join_with_invite(campaign_id, owner, player, role="player")

    # 3. Player can now view session
    res_player_view = client.get(f"/api/v1/sessions/{session_id}", headers=player)
    assert res_player_view.status_code == 200
    assert res_player_view.json()["id"] == session_id

    # 4. Player tries to advance turn (requires 'run_session' / DM) -> 403 Forbidden
    res_player_advance = client.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=player,
        json={"next_character_id": "c2"},
    )
    assert res_player_advance.status_code == 403
    assert res_player_advance.json()["detail"]["required_permission"] == "run_session"

    # 5. The owner runs the session as DM and can advance turn successfully
    res_dm_advance = client.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=owner,
        json={"next_character_id": "c2"},
    )
    assert res_dm_advance.status_code == 200
    assert res_dm_advance.json()["status"] == "turn_advanced"


@pytest.mark.asyncio
async def test_zanzibar_board_view_permission(signing_issuer):
    """Verify board query endpoint requires Zanzibar view permission."""
    owner = _bearer(signing_issuer, "owner_dana")
    spectator = _bearer(signing_issuer, "spectator_devon")
    campaign_id, session_id = _create_campaign_with_session(owner)

    # Owner invites a spectator; the spectator redeems the invite
    _join_with_invite(campaign_id, owner, spectator, role="spectator")

    res = client.get(f"/api/v1/boards/{session_id}", headers=spectator)
    assert res.status_code == 200
    assert "tokens" in res.json()
