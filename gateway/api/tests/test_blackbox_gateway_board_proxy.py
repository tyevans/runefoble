"""Blackbox frontdoor tests for the gateway board and token routes (TASK-0582).

Governed by ADR-0002, ADR-0006, ADR-0007, ADR-0015 and Hard Invariant 7.

- `board_state` runs as a live loopback upstream. The gateway reaches it over HTTP.
- Setup goes through board_state's public routes: `POST /api/v1/boards` and the token routes.
  Campaign roles are written on the shared SpiceDB mock, the process boundary for SpiceDB.
- Every assertion reads a gateway HTTP response. No test reads private state.
- The gateway forwards the caller's bearer only. board_state decides every permission.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from board_state.main import app as board_state_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.ws_identity import bearer

DM = "dm-evelyn"
OWNER = "player-marcus"
STRANGER = "stranger-mallory"


@pytest.fixture
def client(game_session_upstream, board_state_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def campaign(client: TestClient) -> str:
    """The DM creates a campaign and invites OWNER as a player. Both steps go through the gateway."""
    res = client.post("/api/v1/campaigns", json={"title": "Crypt"}, headers=bearer(DM))
    assert res.status_code == 201, res.text
    campaign_id = res.json()["id"]
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=bearer(DM)
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(OWNER),
    )
    assert joined.status_code == 200, joined.text
    return campaign_id


@pytest.fixture
def board(campaign: str, board_state_upstream: str) -> str:
    """Create the board through board_state's public route, as the DM."""
    session_id = f"t0582-{uuid4().hex}"
    res = TestClient(board_state_app).post(
        "/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign, "cols": 12, "rows": 12},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return session_id


@pytest.fixture
def token(board: str, board_state_upstream: str) -> str:
    """Place a DM token at (4, 5) through board_state's public route."""
    token_id = f"ogre-{uuid4().hex[:8]}"
    res = TestClient(board_state_app).post(
        f"/api/v1/boards/{board}/tokens",
        json={"token_id": token_id, "name": "Ogre", "x": 4, "y": 5},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return token_id


def test_a_token_move_through_the_gateway_changes_the_board_the_gateway_reads(
    client: TestClient, board: str, token: str
):
    move = client.post(
        f"/api/v1/boards/{board}/tokens/{token}/move",
        json={"to_x": 6, "to_y": 7},
        headers=bearer(DM),
    )
    assert move.status_code == 200, move.text
    assert (move.json()["x"], move.json()["y"]) == (6, 7)

    read = client.get(f"/api/v1/boards/{board}", headers=bearer(DM))

    assert read.status_code == 200, read.text
    moved = read.json()["tokens"][token]
    assert (moved["x"], moved["y"]) == (6, 7)


def test_get_one_token_returns_the_stored_position(client: TestClient, board: str, token: str):
    res = client.get(f"/api/v1/boards/{board}/tokens/{token}", headers=bearer(DM))

    assert res.status_code == 200, res.text
    assert res.json()["token_id"] == token
    assert (res.json()["x"], res.json()["y"]) == (4, 5)


def test_get_an_unknown_token_returns_404(client: TestClient, board: str):
    res = client.get(f"/api/v1/boards/{board}/tokens/no-such-token", headers=bearer(DM))

    assert res.status_code == 404, res.text


def test_the_sessionless_token_move_route_is_gone(client: TestClient, token: str):
    res = client.post(
        f"/api/v1/board/tokens/{token}/move", json={"to_x": 1, "to_y": 1}, headers=bearer(DM)
    )

    assert res.status_code == 404, res.text


def test_the_sessionless_token_get_route_is_gone(client: TestClient, token: str):
    res = client.get(f"/api/v1/board/tokens/{token}", headers=bearer(DM))

    assert res.status_code == 404, res.text


def test_a_caller_without_a_bearer_is_refused_by_the_gateway(client: TestClient, board: str):
    res = client.get(f"/api/v1/boards/{board}")

    assert res.status_code == 401, res.text


def test_a_campaign_member_reads_the_board_through_the_gateway(
    client: TestClient, board: str, token: str
):
    res = client.get(f"/api/v1/boards/{board}", headers=bearer(OWNER))

    assert res.status_code == 200, res.text
    assert token in res.json()["tokens"]


def test_a_stranger_gets_403_for_the_board_read_through_the_gateway(
    client: TestClient, board: str, token: str
):
    res = client.get(f"/api/v1/boards/{board}", headers=bearer(STRANGER))

    assert res.status_code == 403, res.text
    assert token not in res.text


def test_board_state_decides_the_permission_for_a_stranger(
    client: TestClient, board: str, token: str
):
    """The gateway forwards the bearer. board_state refuses a caller with no board role."""
    move = client.post(
        f"/api/v1/boards/{board}/tokens/{token}/move",
        json={"to_x": 9, "to_y": 9},
        headers=bearer(STRANGER),
    )
    read = client.get(f"/api/v1/boards/{board}/tokens/{token}", headers=bearer(STRANGER))

    assert move.status_code == 403, move.text
    assert read.status_code == 403, read.text
    still_there = client.get(f"/api/v1/boards/{board}/tokens/{token}", headers=bearer(DM))
    assert (still_there.json()["x"], still_there.json()["y"]) == (4, 5)


def test_an_unknown_board_returns_404_through_the_gateway(client: TestClient):
    res = client.get(f"/api/v1/boards/{uuid4()}", headers=bearer(DM))

    assert res.status_code == 404, res.text


def test_board_service_down_returns_503_for_a_board_read(
    monkeypatch, trusted_ws_issuer, board: str
):
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get(f"/api/v1/boards/{board}", headers=bearer(DM))

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "board_state"


def test_board_service_down_returns_503_for_a_token_move(
    monkeypatch, trusted_ws_issuer, board: str, token: str
):
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.post(
            f"/api/v1/boards/{board}/tokens/{token}/move",
            json={"to_x": 1, "to_y": 1},
            headers=bearer(DM),
        )

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "board_state"


def test_a_board_service_5xx_returns_502_through_the_gateway(
    monkeypatch, trusted_ws_issuer, board: str
):
    with serve(unavailable_app(500)) as url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", url)
        with TestClient(gateway_app) as client:
            res = client.get(f"/api/v1/boards/{board}", headers=bearer(DM))

    assert res.status_code == 502, res.text
    assert res.json()["upstream"] == "board_state"
