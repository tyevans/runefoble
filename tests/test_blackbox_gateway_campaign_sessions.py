"""Blackbox frontdoor tests for Gateway Campaign Sessions API and Persistence (TASK-0246).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0005 (Zitadel OIDC), ADR-0007 (Gateway API).
Verifies:
1. Non-members cannot list or create campaign sessions (403 Forbidden via Zanzibar).
2. Campaign members with 'player' or 'spectator' roles can list sessions (Zanzibar 'view'),
   but cannot create sessions (403 Forbidden, lacking Zanzibar 'run_session').
3. Campaign owners and Dungeon Masters can create sessions/lobbies (HTTP 201 Created)
   and list all active, lobby, and upcoming sessions.
4. Strict cross-campaign isolation: session access is bounded to the parent campaign.
5. Reconstituted session metadata is accessible through public gateway endpoints.
"""

import os

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app


@pytest.fixture
def client(game_session_upstream):
    """Enter the gateway lifespan after game_session is served, so the proxy reaches it."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.mark.asyncio
async def test_non_member_cannot_list_or_create_sessions(trusted_ws_issuer, client):
    """Verify non-members are rejected with 403 Forbidden on session routes."""
    headers_owner = _auth(trusted_ws_issuer, "dm_evelyn")
    headers_stranger = _auth(trusted_ws_issuer, "unauthorized_stranger")

    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Curse of Strahd", "setting": "Barovia"},
        headers=headers_owner,
    )
    assert res_camp.status_code == 201
    campaign_id = res_camp.json()["id"]

    # Stranger attempts to list sessions -> 403 Forbidden
    res_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        headers=headers_stranger,
    )
    assert res_list.status_code == 403
    assert res_list.json()["detail"]["error"] == "permission_denied"

    # Stranger attempts to create session -> 403 Forbidden
    res_create = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Illicit Session", "status": "lobby"},
        headers=headers_stranger,
    )
    assert res_create.status_code == 403
    assert res_create.json()["detail"]["error"] == "permission_denied"


@pytest.mark.asyncio
async def test_player_can_list_sessions_but_cannot_create(trusted_ws_issuer, client):
    """Verify members with 'player' role have view access but lack run_session."""
    headers_owner = _auth(trusted_ws_issuer, "dm_evelyn")
    headers_player = _auth(trusted_ws_issuer, "player_valeros")

    # 1. Owner creates campaign
    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Lost Mine of Phandelver"},
        headers=headers_owner,
    )
    campaign_id = res_camp.json()["id"]

    # 2. Generate player invite and player joins
    res_inv = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers=headers_owner,
    )
    token = res_inv.json()["token"]

    res_join = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_player,
    )
    assert res_join.status_code == 200

    # 3. Player lists sessions -> 200 OK (contains initial staging lobby)
    res_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        headers=headers_player,
    )
    assert res_list.status_code == 200
    sessions = res_list.json()
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Session #1: Staging Lobby"
    assert sessions[0]["status"] == "lobby"

    # 4. Player attempts to create session -> 403 Forbidden (requires 'run_session')
    res_create = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Unauthorized Player Lobby", "status": "lobby"},
        headers=headers_player,
    )
    assert res_create.status_code == 403
    assert res_create.json()["detail"]["error"] == "permission_denied"


@pytest.mark.asyncio
async def test_spectator_can_list_sessions_but_cannot_create(trusted_ws_issuer, client):
    """Verify members with 'spectator' role have view access but lack run_session."""
    headers_owner = _auth(trusted_ws_issuer, "dm_evelyn")
    headers_spectator = _auth(trusted_ws_issuer, "spectator_clara")

    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Arena of Champions"},
        headers=headers_owner,
    )
    campaign_id = res_camp.json()["id"]

    res_inv = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "spectator"},
        headers=headers_owner,
    )
    token = res_inv.json()["token"]

    client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_spectator,
    )

    # Spectator can list sessions (contains seeded staging lobby)
    res_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        headers=headers_spectator,
    )
    assert res_list.status_code == 200
    sessions = res_list.json()
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Session #1: Staging Lobby"

    # Spectator cannot create sessions
    res_create = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Spectator Staging"},
        headers=headers_spectator,
    )
    assert res_create.status_code == 403


@pytest.mark.asyncio
async def test_owner_and_dm_create_and_list_sessions(trusted_ws_issuer, client):
    """Verify campaign owners and DMs can create sessions and list them."""
    headers_owner = _auth(trusted_ws_issuer, "owner_merlin")
    headers_dm = _auth(trusted_ws_issuer, "dm_arthur")
    headers_player = _auth(trusted_ws_issuer, "player_lancelot")

    # 1. Owner creates campaign
    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Camelot Chronicles"},
        headers=headers_owner,
    )
    campaign_id = res_camp.json()["id"]

    # 2. Assign Arthur as dungeon_master and Lancelot as player
    client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_arthur", "role": "dungeon_master"},
        headers=headers_owner,
    )
    client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "player_lancelot", "role": "player"},
        headers=headers_owner,
    )

    # 3. Owner creates Session 1 (lobby)
    res_sess1 = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={
            "title": "Session #1: The Round Table Assembles",
            "status": "lobby",
            "description": "Pre-game character staging and readiness check.",
        },
        headers=headers_owner,
    )
    assert res_sess1.status_code == 201
    s1_data = res_sess1.json()
    assert s1_data["title"] == "Session #1: The Round Table Assembles"
    assert s1_data["status"] == "lobby"
    assert s1_data["campaign_id"] == campaign_id
    assert s1_data["round"] == 1
    assert s1_data["participants_count"] == 0
    assert s1_data["id"].startswith("session-")
    assert "created_at" in s1_data

    # 4. DM Arthur creates Session 2 (upcoming scheduled)
    res_sess2 = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={
            "title": "Session #2: Quest for the Holy Grail",
            "status": "upcoming",
            "scheduled_at": "2026-10-15T18:00:00Z",
            "description": "Departure across the perilous forest.",
        },
        headers=headers_dm,
    )
    assert res_sess2.status_code == 201
    s2_data = res_sess2.json()
    assert s2_data["title"] == "Session #2: Quest for the Holy Grail"
    assert s2_data["status"] == "upcoming"
    assert s2_data["scheduled_at"] == "2026-10-15T18:00:00Z"

    # 5. Player Lancelot lists sessions and sees all (initial lobby + 2 created)
    res_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        headers=headers_player,
    )
    assert res_list.status_code == 200
    sessions = res_list.json()
    assert len(sessions) == 3
    session_titles = [s["title"] for s in sessions]
    assert "Session #1: Staging Lobby" in session_titles
    assert "Session #1: The Round Table Assembles" in session_titles
    assert "Session #2: Quest for the Holy Grail" in session_titles

    # 6. Retrieve session details via session proxy
    owned_session_id = _owner_session(campaign_id, headers_owner)
    res_detail = client.get(f"/api/v1/sessions/{owned_session_id}", headers=headers_owner)
    assert res_detail.status_code == 200
    assert res_detail.json()["session_id"] == owned_session_id


@pytest.mark.asyncio
async def test_cross_campaign_session_isolation(trusted_ws_issuer, client):
    """Verify sessions are isolated and never leak across campaigns."""
    headers_a = _auth(trusted_ws_issuer, "dm_alice")
    headers_b = _auth(trusted_ws_issuer, "dm_bob")

    # Alice creates Campaign A and Session A
    res_a = client.post(
        "/api/v1/campaigns",
        json={"title": "Campaign Alpha"},
        headers=headers_a,
    )
    camp_a = res_a.json()["id"]

    res_sa = client.post(
        f"/api/v1/campaigns/{camp_a}/sessions",
        json={"title": "Alpha Session 1"},
        headers=headers_a,
    )
    assert res_sa.status_code == 201

    # Bob creates Campaign B and Session B
    res_b = client.post(
        "/api/v1/campaigns",
        json={"title": "Campaign Beta"},
        headers=headers_b,
    )
    camp_b = res_b.json()["id"]

    res_sb = client.post(
        f"/api/v1/campaigns/{camp_b}/sessions",
        json={"title": "Beta Session 1"},
        headers=headers_b,
    )
    assert res_sb.status_code == 201

    # Alice queries Campaign A sessions -> gets initial lobby and Alpha Session 1
    alice_sessions = client.get(f"/api/v1/campaigns/{camp_a}/sessions", headers=headers_a).json()
    assert len(alice_sessions) == 2
    alice_titles = [s["title"] for s in alice_sessions]
    assert "Session #1: Staging Lobby" in alice_titles
    assert "Alpha Session 1" in alice_titles

    # Bob queries Campaign B sessions -> gets initial lobby and Beta Session 1
    bob_sessions = client.get(f"/api/v1/campaigns/{camp_b}/sessions", headers=headers_b).json()
    assert len(bob_sessions) == 2
    bob_titles = [s["title"] for s in bob_sessions]
    assert "Session #1: Staging Lobby" in bob_titles
    assert "Beta Session 1" in bob_titles

    # Bob tries to access Campaign A sessions -> 403 Forbidden
    res_forbidden = client.get(f"/api/v1/campaigns/{camp_a}/sessions", headers=headers_b)
    assert res_forbidden.status_code == 403


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
