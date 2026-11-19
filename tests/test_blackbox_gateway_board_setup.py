"""Gateway frontdoor tests for the DM battlemap set-up flow (TASK-0922).

The DM creates the session board and places the party tokens through the gateway. The gateway
forwards the bearer token. board_state checks `campaign.run_session` to create the board and the
token permissions to place a token. Setup uses only public routes: the gateway campaign, invite,
character and join routes. Governed by ADR-0001, ADR-0014, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url
from tests.helpers.ws_identity import bearer, ws_subprotocols

DM = "dm-evelyn"
PLAYER = "player-valeros"
SILENCE_SECONDS = 1.0


def _frame_within(ws, seconds: float) -> dict[str, Any] | None:
    """Return the next frame, or None when no frame arrives within `seconds`."""
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(ws.receive_json)
    try:
        return pending.result(timeout=seconds)
    except FutureTimeout:
        return None
    finally:
        pool.shutdown(wait=False)


@pytest.fixture
def gateway(
    game_session_upstream: str, character_sheet_upstream: str, board_state_upstream: str
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


def _seated_table(gateway: TestClient) -> tuple[str, str, str]:
    """Create a campaign and session as the DM, and seat the player with a campaign character.

    Returns (campaign_id, session_id, character_id).
    """
    campaign = gateway.post("/api/v1/campaigns", json={"title": "Crypt"}, headers=bearer(DM))
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    session = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/sessions", json={"title": "Night 1"}, headers=bearer(DM)
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
    character = gateway.post(
        "/api/v1/characters",
        json={"name": "Valeros", "characterClass": "Fighter", "campaignId": campaign_id},
        headers=bearer(PLAYER),
    )
    assert character.status_code in (200, 201), character.text
    character_id = character.json()["id"]
    seat = gateway.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": character_id,
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
        headers=bearer(PLAYER),
    )
    assert seat.status_code == 200, seat.text
    return campaign_id, session_id, character_id


def _create_board(gateway: TestClient, campaign_id: str, session_id: str, user: str):
    return gateway.post(
        "/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": 12, "rows": 9},
        headers=bearer(user),
    )


def test_dm_creates_the_board_and_places_a_party_token_through_the_gateway(
    gateway: TestClient,
) -> None:
    campaign_id, session_id, character_id = _seated_table(gateway)

    created = _create_board(gateway, campaign_id, session_id, DM)
    assert created.status_code == 200, created.text
    placed = gateway.post(
        f"/api/v1/boards/{session_id}/tokens",
        json={"name": "Valeros", "token_type": "pc", "x": 0, "y": 0, "character_id": character_id},
        headers=bearer(DM),
    )
    assert placed.status_code == 200, placed.text
    token_id = placed.json()["token_id"]

    board = gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(PLAYER))
    assert board.status_code == 200, board.text
    assert (board.json()["cols"], board.json()["rows"]) == (12, 9)
    token = gateway.get(f"/api/v1/boards/{session_id}/tokens/{token_id}", headers=bearer(PLAYER))
    assert token.status_code == 200, token.text
    assert (token.json()["name"], token.json()["x"], token.json()["y"]) == ("Valeros", 0, 0)


def test_the_player_can_move_the_token_that_the_dm_placed_for_the_character(
    gateway: TestClient,
) -> None:
    campaign_id, session_id, character_id = _seated_table(gateway)
    assert _create_board(gateway, campaign_id, session_id, DM).status_code == 200
    placed = gateway.post(
        f"/api/v1/boards/{session_id}/tokens",
        json={"name": "Valeros", "token_type": "pc", "x": 0, "y": 0, "character_id": character_id},
        headers=bearer(DM),
    )
    token_id = placed.json()["token_id"]

    moved = gateway.post(
        f"/api/v1/boards/{session_id}/tokens/{token_id}/move",
        json={"to_x": 1, "to_y": 1},
        headers=bearer(PLAYER),
    )

    assert moved.status_code == 200, moved.text
    assert (moved.json()["x"], moved.json()["y"]) == (1, 1)


def test_a_player_gets_the_owner_403_on_board_create(gateway: TestClient) -> None:
    campaign_id, session_id, _ = _seated_table(gateway)

    refused = _create_board(gateway, campaign_id, session_id, PLAYER)

    assert refused.status_code == 403, refused.text
    assert gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(DM)).status_code == 404


def test_a_player_gets_the_owner_403_on_a_non_character_token(gateway: TestClient) -> None:
    campaign_id, session_id, _ = _seated_table(gateway)
    assert _create_board(gateway, campaign_id, session_id, DM).status_code == 200

    refused = gateway.post(
        f"/api/v1/boards/{session_id}/tokens",
        json={"name": "Boulder", "token_type": "obstacle", "x": 3, "y": 3},
        headers=bearer(PLAYER),
    )

    assert refused.status_code == 403, refused.text
    assert gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(DM)).json()["tokens"] == {}


def test_a_second_create_returns_the_owner_409(gateway: TestClient) -> None:
    campaign_id, session_id, _ = _seated_table(gateway)
    assert _create_board(gateway, campaign_id, session_id, DM).status_code == 200

    again = _create_board(gateway, campaign_id, session_id, DM)

    assert again.status_code == 409, again.text


def test_dm_board_create_sends_one_board_ready_frame_to_each_session_socket(
    gateway: TestClient,
) -> None:
    campaign_id, session_id, _ = _seated_table(gateway)
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
    ):
        assert dm.receive_json()["type"] == "connected"
        assert player.receive_json()["type"] == "connected"

        assert _create_board(gateway, campaign_id, session_id, DM).status_code == 200

        expected = {"type": "board_ready", "sessionId": session_id}
        assert dm.receive_json() == expected
        assert player.receive_json() == expected
        assert _frame_within(dm, SILENCE_SECONDS) is None
        assert _frame_within(player, SILENCE_SECONDS) is None


def test_a_refused_board_create_sends_no_board_ready_frame(gateway: TestClient) -> None:
    campaign_id, session_id, _ = _seated_table(gateway)
    path = f"/ws/session/{session_id}"

    with gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm:
        assert dm.receive_json()["type"] == "connected"

        assert _create_board(gateway, campaign_id, session_id, PLAYER).status_code == 403

        assert _frame_within(dm, SILENCE_SECONDS) is None


def _party_token(name: str, character_id: str, x: int) -> dict[str, Any]:
    return {"name": name, "token_type": "pc", "x": x, "y": 0, "character_id": character_id}


def test_dm_set_up_sends_one_board_ready_after_the_party_tokens_are_placed(
    gateway: TestClient,
) -> None:
    """The set-up call creates the board and places the tokens. Then each socket gets one frame."""
    campaign_id, session_id, character_id = _seated_table(gateway)
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
    ):
        assert dm.receive_json()["type"] == "connected"
        assert player.receive_json()["type"] == "connected"

        set_up = gateway.post(
            "/api/v1/boards",
            json={
                "campaign_id": campaign_id,
                "session_id": session_id,
                "tokens": [_party_token("Valeros", character_id, 0)],
            },
            headers=bearer(DM),
        )
        assert set_up.status_code == 200, set_up.text
        assert [t["name"] for t in set_up.json()["tokens"]] == ["Valeros"]

        expected = {"type": "board_ready", "sessionId": session_id}
        for ws in (dm, player):
            assert ws.receive_json() == expected
            board = gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(PLAYER))
            assert board.status_code == 200, board.text
            assert [t["name"] for t in board.json()["tokens"].values()] == ["Valeros"]
        assert _frame_within(dm, SILENCE_SECONDS) is None
        assert _frame_within(player, SILENCE_SECONDS) is None


def test_a_refused_party_token_stops_the_set_up_and_names_the_token(gateway: TestClient) -> None:
    """The board exists after a refused token, so the frame still goes out once."""
    campaign_id, session_id, character_id = _seated_table(gateway)
    path = f"/ws/session/{session_id}"

    with gateway.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player:
        assert player.receive_json()["type"] == "connected"

        set_up = gateway.post(
            "/api/v1/boards",
            json={
                "campaign_id": campaign_id,
                "session_id": session_id,
                "tokens": [
                    _party_token("Valeros", character_id, 0),
                    _party_token("Ghost", str(uuid4()), 1),
                    _party_token("Kyra", character_id, 2),
                ],
            },
            headers=bearer(DM),
        )

        assert set_up.status_code == 403, set_up.text
        assert set_up.json()["board_created"] is True
        assert set_up.json()["token"] == "Ghost"
        assert set_up.json()["detail"].startswith("Ghost: ")
        assert player.receive_json() == {"type": "board_ready", "sessionId": session_id}
        assert _frame_within(player, SILENCE_SECONDS) is None
    board = gateway.get(f"/api/v1/boards/{session_id}", headers=bearer(PLAYER))
    assert [t["name"] for t in board.json()["tokens"].values()] == ["Valeros"]


def test_unreachable_board_owner_gives_503(
    monkeypatch: pytest.MonkeyPatch, trusted_ws_issuer
) -> None:
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        created = client.post(
            "/api/v1/boards",
            json={"campaign_id": "c-1", "session_id": "s-1"},
            headers=bearer(DM),
        )
        placed = client.post(
            "/api/v1/boards/s-1/tokens",
            json={"name": "Valeros", "token_type": "pc", "x": 0, "y": 0},
            headers=bearer(DM),
        )

    assert created.status_code == 503, created.text
    assert placed.status_code == 503, placed.text
