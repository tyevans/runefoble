"""A seated player drags the party token that the DM set-up placed (defect found on Kind).

The DM sets up the session board with one gateway call, `POST /api/v1/boards` with the party
`tokens` (TASK-0928). The player then opens the board socket `/ws/boards/{id}` on board_state,
as the Kind ingress routes it, and sends `confirm_move` for the token of his character.
The player must get a `token_moved` frame, and a board read must show the new cell.
A refused or incomplete move gets one `error` frame that names the action, so the board UI
can show it. The token stays where it was.

Setup uses public routes only: the gateway campaign, invite, character, seat and board routes.
Governed by Hard Invariant 7, ADR-0001, ADR-0014 and ADR-0015.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from websockets.sync.client import ClientConnection, connect

from tests.helpers.ws_identity import bearer, ws_subprotocols

DM = "dm-evelyn"
PLAYER = "player-valeros"
OTHER_PLAYER = "player-sarah"
FRAME_SECONDS = 5.0


@pytest.fixture
def gateway(
    game_session_upstream: str, character_sheet_upstream: str, board_state_upstream: str
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


def _ok(response, *codes: int) -> dict[str, Any]:
    assert response.status_code in (codes or (200,)), response.text
    return response.json()


def _seated_table(gateway: TestClient) -> tuple[str, str, str]:
    """The DM runs a campaign and a session. The player joins and seats Valeros.

    Returns (campaign_id, session_id, character_id).
    """
    campaign_id = _ok(
        gateway.post("/api/v1/campaigns", json={"title": "Crypt"}, headers=bearer(DM)), 201
    )["id"]
    session_id = _ok(
        gateway.post(
            f"/api/v1/campaigns/{campaign_id}/sessions",
            json={"title": "Night 1"},
            headers=bearer(DM),
        ),
        201,
    )["id"]
    invite = _ok(
        gateway.post(
            f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=bearer(DM)
        ),
        201,
    )
    for user in (PLAYER, OTHER_PLAYER):
        _ok(
            gateway.post(
                "/api/v1/campaigns/join",
                json={"invite_token": invite["token"]},
                headers=bearer(user),
            )
        )
    character_id = _ok(
        gateway.post(
            "/api/v1/characters",
            json={
                "name": "Valeros the Bold",
                "characterClass": "Fighter",
                "campaignId": campaign_id,
            },
            headers=bearer(PLAYER),
        ),
        200,
        201,
    )["id"]
    _ok(
        gateway.post(
            f"/api/v1/sessions/{session_id}/join",
            json={
                "character_id": character_id,
                "character_name": "Valeros the Bold",
                "character_class": "Fighter",
            },
            headers=bearer(PLAYER),
        )
    )
    return campaign_id, session_id, character_id


def _set_up(gateway: TestClient, campaign_id: str, session_id: str, character_id: str):
    """The body that `<runefoble-board-empty>` sends (board-setup.ts `buildSetUpBoardBody`)."""
    return gateway.post(
        "/api/v1/boards",
        json={
            "campaign_id": campaign_id,
            "session_id": session_id,
            "cols": 10,
            "rows": 10,
            "tokens": [
                {
                    "name": "Valeros the Bold",
                    "token_type": "pc",
                    "x": 0,
                    "y": 0,
                    "character_id": character_id,
                }
            ],
        },
        headers=bearer(DM),
    )


def _board_socket(board_url: str, session_id: str, user: str) -> ClientConnection:
    url = board_url.replace("http://", "ws://", 1) + f"/ws/boards/{session_id}"
    return connect(url, subprotocols=ws_subprotocols(user), open_timeout=FRAME_SECONDS)


def _next_frame(ws: ClientConnection) -> dict[str, Any]:
    return json.loads(ws.recv(timeout=FRAME_SECONDS))


def _move(token_id: str, **fields: Any) -> str:
    frame = {"action": "confirm_move", "token_id": token_id, "initiated_by": "player", **fields}
    return json.dumps(frame)


def _set_up_table(gateway: TestClient) -> tuple[str, str]:
    """Seat Valeros and set up the board. Returns (session_id, token_id)."""
    campaign_id, session_id, character_id = _seated_table(gateway)
    set_up = _ok(_set_up(gateway, campaign_id, session_id, character_id))
    return session_id, set_up["tokens"][0]["token_id"]


def _token_cell(gateway: TestClient, session_id: str, token_id: str) -> tuple[int, int]:
    token = _ok(
        gateway.get(f"/api/v1/boards/{session_id}/tokens/{token_id}", headers=bearer(PLAYER))
    )
    return token["x"], token["y"]


def test_the_seated_player_drags_his_party_token_on_the_board_socket(
    gateway: TestClient, board_state_upstream: str
) -> None:
    session_id, token_id = _set_up_table(gateway)

    with _board_socket(board_state_upstream, session_id, PLAYER) as ws:
        assert _next_frame(ws)["type"] == "connected"
        ws.send(_move(token_id, to_x=3, to_y=3))
        frame = _next_frame(ws)

    assert frame.get("type") == "token_moved", frame
    assert (frame["token_id"], frame["x"], frame["y"]) == (token_id, 3, 3)
    assert _token_cell(gateway, session_id, token_id) == (3, 3)


def test_another_player_gets_a_permission_error_frame_and_the_token_stays(
    gateway: TestClient, board_state_upstream: str
) -> None:
    session_id, token_id = _set_up_table(gateway)

    with _board_socket(board_state_upstream, session_id, OTHER_PLAYER) as ws:
        assert _next_frame(ws)["type"] == "connected"
        ws.send(_move(token_id, to_x=3, to_y=3))
        frame = _next_frame(ws)

    assert frame["type"] == "error", frame
    assert (frame["code"], frame["action"], frame["token_id"]) == (
        "PERMISSION_DENIED",
        "confirm_move",
        token_id,
    )
    assert frame["message"]
    assert _token_cell(gateway, session_id, token_id) == (0, 0)


def test_a_move_without_a_target_cell_gets_an_invalid_error_frame(
    gateway: TestClient, board_state_upstream: str
) -> None:
    session_id, token_id = _set_up_table(gateway)

    with _board_socket(board_state_upstream, session_id, PLAYER) as ws:
        assert _next_frame(ws)["type"] == "connected"
        ws.send(_move(token_id, to_x=3))
        frame = _next_frame(ws)

    assert frame["type"] == "error", frame
    assert (frame["code"], frame["action"]) == ("INVALID", "confirm_move")
    assert "to_y" in frame["message"]
    assert _token_cell(gateway, session_id, token_id) == (0, 0)
