"""Tests for Gateway API Zanzibar object-level authorization.

Setup runs through public frontdoors only. The owner creates a campaign, and
members redeem invite tokens. No test writes SpiceDB tuples directly (ADR-0015 a, d).
"""

import os

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer


@pytest.fixture
def client(game_session_upstream, board_state_upstream):
    """Enter the gateway lifespan after game_session and board_state are served."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def _bearer(issuer: SigningTestIssuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_campaign_with_session(
    client: TestClient, owner_headers: dict[str, str]
) -> tuple[str, str]:
    """Create a campaign as the owner and return (campaign_id, first_session_id)."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Zanzibar Authorization Campaign"},
        headers=owner_headers,
    )
    assert res.status_code == 201
    campaign_id = res.json()["id"]

    return campaign_id, _owner_session(campaign_id, owner_headers)


def _join_with_invite(
    client: TestClient,
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
async def test_zanzibar_authorization_enforcement(trusted_ws_issuer, client):
    """Verify that Gateway API enforces SpiceDB Zanzibar permissions without hardcoded role checks."""
    owner = _bearer(trusted_ws_issuer, "owner_dana")
    player = _bearer(trusted_ws_issuer, "player_alice")
    stranger = _bearer(trusted_ws_issuer, "stranger_bob")
    campaign_id, session_id = _create_campaign_with_session(client, owner)

    # 1. Unassigned user tries to view session -> 403 Forbidden
    res_unauth = client.get(f"/api/v1/sessions/{session_id}", headers=stranger)
    assert res_unauth.status_code == 403
    err_data = res_unauth.json()["detail"]
    assert err_data["error"] == "permission_denied"
    assert err_data["required_permission"] == "observe"

    # 2. Owner invites the player; the player redeems the invite
    _join_with_invite(client, campaign_id, owner, player, role="player")

    # 3. Player can now view session
    res_player_view = client.get(f"/api/v1/sessions/{session_id}", headers=player)
    assert res_player_view.status_code == 200
    assert res_player_view.json()["session_id"] == session_id

    # 4. Player tries to advance turn (requires 'control' on the session, which is run_session on its campaign) -> 403 Forbidden
    res_player_advance = client.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=player,
        json={"next_character_id": "c2"},
    )
    assert res_player_advance.status_code == 403
    assert res_player_advance.json()["detail"]["required_permission"] == "control"

    # 5. The owner runs the session as DM and can advance turn successfully
    assert client.post(f"/api/v1/sessions/{session_id}/start", headers=owner).status_code == 200
    res_dm_advance = client.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=owner,
        json={"next_character_id": "c2"},
    )
    assert res_dm_advance.status_code == 200
    assert client.get(f"/api/v1/sessions/{session_id}", headers=owner).json()["current_turn"] == 2


@pytest.mark.asyncio
async def test_zanzibar_board_view_permission(trusted_ws_issuer, client):
    """Verify board query endpoint requires Zanzibar view permission."""
    owner = _bearer(trusted_ws_issuer, "owner_dana")
    spectator = _bearer(trusted_ws_issuer, "spectator_devon")
    campaign_id, session_id = _create_campaign_with_session(client, owner)
    _owner_board(campaign_id, session_id, owner)

    # Owner invites a spectator; the spectator redeems the invite
    _join_with_invite(client, campaign_id, owner, spectator, role="spectator")

    res = client.get(f"/api/v1/boards/{session_id}", headers=spectator)
    assert res.status_code == 200
    assert "tokens" in res.json()


def _owner_board(campaign_id: str, session_id: str, headers: dict[str, str]) -> None:
    """Create the session board through board_state's public route, as the campaign owner."""
    url = os.environ["RUNEFOBLE_BOARD_STATE_URL"]
    res = httpx.post(
        f"{url}/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign_id},
        headers=headers,
        timeout=5.0,
    )
    assert res.status_code == 200, res.text


def _owner_session(campaign_id: str, headers: dict[str, str]) -> str:
    """Create a game session in a campaign through the owner's public game_session route."""
    url = os.environ["RUNEFOBLE_GAME_SESSION_URL"]
    res = httpx.post(
        f"{url}/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Crypt"},
        headers=headers,
        timeout=5.0,
    )
    assert res.status_code == 200, res.text
    return res.json()["session_id"]
