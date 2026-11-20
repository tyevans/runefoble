"""Gateway frontdoor tests for arming a secret DM trap (TASK-0954).

The DM board control "Arm Cell" posts to `POST /api/v1/boards/{session_id}/traps` through the
gateway. The gateway forwards the bearer token. board_state checks `board.manage_traps`, so the
DM may arm a trap and a player may not. Setup uses only public routes. Governed by ADR-0001,
ADR-0014, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.ws_identity import bearer

DM = "dm-evelyn"
PLAYER = "player-valeros"


@pytest.fixture
def gateway(
    game_session_upstream: str, character_sheet_upstream: str, board_state_upstream: str
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


def _session_with_board(gateway: TestClient) -> str:
    """The DM creates a campaign, a session and a board. Returns the session id."""
    campaign = gateway.post("/api/v1/campaigns", json={"title": "Catacombs"}, headers=bearer(DM))
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    session = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/sessions", json={"title": "Night 2"}, headers=bearer(DM)
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["id"]
    invite = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=bearer(DM)
    )
    assert invite.status_code == 201, invite.text
    joined = gateway.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(PLAYER),
    )
    assert joined.status_code == 200, joined.text
    board = gateway.post(
        "/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": 10, "rows": 10},
        headers=bearer(DM),
    )
    assert board.status_code in (200, 201), board.text
    return session_id


def _trap_body() -> dict[str, object]:
    return {
        "name": "Spike Pit",
        "trap_type": "pit_trap",
        "x": 4,
        "y": 5,
        "trigger_type": "step",
        "proximity_radius": 1,
        "dc_detection": 15,
        "damage_dice": "2d10",
        "is_secret": True,
    }


def test_dm_arms_a_secret_trap_through_the_gateway(gateway: TestClient) -> None:
    session_id = _session_with_board(gateway)
    res = gateway.post(f"/api/v1/boards/{session_id}/traps", json=_trap_body(), headers=bearer(DM))
    assert res.status_code == 201, res.text
    assert res.json()["name"] == "Spike Pit"

    listed = gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(DM))
    assert listed.status_code == 200, listed.text
    assert "Spike Pit" in listed.text


def test_player_cannot_arm_a_trap_through_the_gateway(gateway: TestClient) -> None:
    session_id = _session_with_board(gateway)
    res = gateway.post(
        f"/api/v1/boards/{session_id}/traps", json=_trap_body(), headers=bearer(PLAYER)
    )
    assert res.status_code == 403, res.text
