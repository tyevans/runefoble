"""Tests for Gateway API Zanzibar object-level authorization.

Setup runs through public frontdoors only. The owner creates a campaign, and
members redeem invite tokens. No test writes SpiceDB tuples directly (ADR-0015 a, d).
"""

import os

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app

from tests.helpers.campaign_setup import create_campaign, create_owner_session, invite_and_join
from tests.helpers.ws_identity import bearer


@pytest.fixture
def client(game_session_upstream, board_state_upstream):
    """Enter the gateway lifespan after game_session and board_state are served."""
    with TestClient(app) as gateway_client:
        yield gateway_client


@pytest.mark.asyncio
async def test_zanzibar_authorization_enforcement(trusted_ws_issuer, client):
    """Verify that Gateway API enforces SpiceDB Zanzibar permissions without hardcoded role checks."""
    owner_id = "owner_dana"
    owner = bearer(owner_id, issuer=trusted_ws_issuer)
    player_id = "player_alice"
    player = bearer(player_id, issuer=trusted_ws_issuer)
    stranger_id = "stranger_bob"
    stranger = bearer(stranger_id, issuer=trusted_ws_issuer)
    campaign_id = create_campaign(client, owner_id)
    session_id = create_owner_session(os.environ["RUNEFOBLE_GAME_SESSION_URL"], owner, campaign_id)

    # 1. Unassigned user tries to view session -> 403 Forbidden
    res_unauth = client.get(f"/api/v1/sessions/{session_id}", headers=stranger)
    assert res_unauth.status_code == 403
    err_data = res_unauth.json()["detail"]
    assert err_data["error"] == "permission_denied"
    assert err_data["required_permission"] == "observe"

    # 2. Owner invites the player; the player redeems the invite
    invite_and_join(client, campaign_id, owner_id, player_id, role="player")

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
    owner_id = "owner_dana"
    owner = bearer(owner_id, issuer=trusted_ws_issuer)
    spectator_id = "spectator_devon"
    spectator = bearer(spectator_id, issuer=trusted_ws_issuer)
    stranger_id = "stranger_mallory"
    stranger = bearer(stranger_id, issuer=trusted_ws_issuer)
    campaign_id = create_campaign(client, owner_id)
    session_id = create_owner_session(os.environ["RUNEFOBLE_GAME_SESSION_URL"], owner, campaign_id)
    _owner_board(campaign_id, session_id, owner)

    # Owner invites a spectator; the spectator redeems the invite
    invite_and_join(client, campaign_id, owner_id, spectator_id, role="spectator")

    res = client.get(f"/api/v1/boards/{session_id}", headers=spectator)
    assert res.status_code == 200
    assert "tokens" in res.json()
    # board_state decides: a caller with no campaign role gets 403 through the gateway.
    refused = client.get(f"/api/v1/boards/{session_id}", headers=stranger)
    assert refused.status_code == 403


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
