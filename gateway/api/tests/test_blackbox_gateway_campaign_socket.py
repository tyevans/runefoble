"""Blackbox frontdoor tests for the campaign socket action relay (TASK-0883).

Governed by ADR-0001, ADR-0014, ADR-0015 (a, b, c) and Hard Invariant 2.

- game_session, board_state and character_sheet run as live loopback owners.
- Setup goes through public HTTP routes only: campaigns, invites, sessions, boards, tokens and
  characters. No test writes owner state.
- Each action is sent as a WebSocket frame that names its session. Every assertion reads the
  frame the socket returns, a gateway or owner HTTP answer, or the owner events on the bus.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url
from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm-evelyn"
PLAYER = "player-marcus"
OTHER_PLAYER = "player-nadia"
SPECTATOR = "spectator-sam"


@pytest.fixture
def client(
    game_session_upstream, board_state_upstream, character_sheet_upstream
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _join(client: TestClient, campaign_id: str, member: str, role: str = "player") -> None:
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": role}, headers=bearer(DM)
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(member),
    )
    assert joined.status_code == 200, joined.text


def _new_campaign(client: TestClient) -> tuple[str, str]:
    """The DM creates a campaign. Return (campaign_id, its first session id)."""
    created = client.post("/api/v1/campaigns", json={"title": "Crypt"}, headers=bearer(DM))
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]
    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(DM))
    assert sessions.status_code == 200, sessions.text
    return campaign_id, str(sessions.json()[0]["id"])


@pytest.fixture
def campaign(client: TestClient) -> tuple[str, str]:
    campaign_id, session_id = _new_campaign(client)
    _join(client, campaign_id, PLAYER)
    return campaign_id, session_id


@pytest.fixture
def board(campaign: tuple[str, str], board_state_upstream: str) -> str:
    """Create the board of the session through board_state's public route, as the DM."""
    campaign_id, session_id = campaign
    res = httpx.post(
        f"{board_state_upstream}/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign_id, "cols": 12, "rows": 12},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return session_id


@pytest.fixture
def token(board: str, board_state_upstream: str) -> str:
    token_id = f"ogre-{uuid4().hex[:8]}"
    res = httpx.post(
        f"{board_state_upstream}/api/v1/boards/{board}/tokens",
        json={"token_id": token_id, "name": "Ogre", "x": 4, "y": 5},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return token_id


def _open(client: TestClient, campaign_id: str, subject: str):
    """Return the campaign socket context for `subject`. The caller reads the connected frame."""
    return client.websocket_connect(
        f"/ws/campaigns/{campaign_id}", subprotocols=ws_subprotocols(subject)
    )


def test_dm_move_token_reaches_the_owner_and_the_socket_relays_applied(
    client: TestClient, campaign: tuple[str, str], board: str, token: str
):
    campaign_id, session_id = campaign
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "move_token",
                "session_id": session_id,
                "token_id": token,
                "to_x": 6,
                "to_y": 7,
            }
        )
        frame = ws.receive_json()

    assert frame["type"] == "move_token"
    assert frame["status"] == "applied"
    assert frame["campaign_id"] == campaign_id
    assert frame["user_id"] == DM
    read = client.get(f"/api/v1/boards/{board}/tokens/{token}", headers=bearer(DM))
    assert (read.json()["x"], read.json()["y"]) == (6, 7)


def test_gateway_publishes_no_event_and_the_owner_publishes_its_own(
    client: TestClient, campaign: tuple[str, str], board: str, token: str, mock_bus
):
    campaign_id, session_id = campaign
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "move_token",
                "session_id": session_id,
                "token_id": token,
                "to_x": 1,
                "to_y": 1,
            }
        )
        assert ws.receive_json()["status"] == "applied"

    published = [str(entry) for stream in mock_bus.streams.values() for entry in stream]
    assert not any("runefoble.events.move_token" in entry for entry in published)
    assert any(token in entry for entry in published)


def test_player_gets_the_owner_403_as_an_error_frame(
    client: TestClient, campaign: tuple[str, str], board: str, mock_bus
):
    campaign_id, session_id = campaign
    with _open(client, campaign_id, PLAYER) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "spawn_monster",
                "session_id": session_id,
                "monster_name": "Ancient Red Dragon",
                "x": 5,
                "y": 5,
            }
        )
        frame = ws.receive_json()

    assert frame["type"] == "error"
    assert frame["code"] == "PERMISSION_DENIED"
    assert frame["action"] == "spawn_monster"
    assert frame["status_code"] == 403
    assert not any(
        "runefoble.events.spawn_monster" in str(entry)
        for stream in mock_bus.streams.values()
        for entry in stream
    )


def test_a_frame_for_a_session_of_another_campaign_is_refused(
    client: TestClient, campaign: tuple[str, str]
):
    campaign_id, _ = campaign
    _, other_session_id = _new_campaign(client)
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {"action": "end_session", "session_id": other_session_id},
        )
        frame = ws.receive_json()

    assert frame["type"] == "error"
    assert frame["code"] == "PERMISSION_DENIED"
    assert frame["action"] == "end_session"
    read = client.get(f"/api/v1/sessions/{other_session_id}", headers=bearer(DM))
    assert read.json()["status"] == "lobby"


def test_dm_ends_the_session_through_the_owner(client: TestClient, campaign: tuple[str, str]):
    campaign_id, session_id = campaign
    started = client.post(f"/api/v1/sessions/{session_id}/start", headers=bearer(DM))
    assert started.status_code == 200, started.text
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "end_session", "session_id": session_id})
        frame = ws.receive_json()

    assert frame["status"] == "applied"
    read = client.get(f"/api/v1/sessions/{session_id}", headers=bearer(DM))
    assert read.json()["status"] == "ended"


def test_a_player_cannot_end_the_session(client: TestClient, campaign: tuple[str, str]):
    campaign_id, session_id = campaign
    with _open(client, campaign_id, PLAYER) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "end_session", "session_id": session_id})
        frame = ws.receive_json()

    assert frame["code"] == "PERMISSION_DENIED"
    assert frame["status_code"] == 403
    read = client.get(f"/api/v1/sessions/{session_id}", headers=bearer(DM))
    assert read.json()["status"] == "lobby"


@pytest.mark.parametrize("action", ["toggle_light", "set_scene", "ghost_preview", "not_an_action"])
def test_an_action_without_an_owner_route_gets_an_error_frame(
    client: TestClient, campaign: tuple[str, str], action: str
):
    campaign_id, session_id = campaign
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": action, "session_id": session_id})
        frame = ws.receive_json()

    assert frame["type"] == "error"
    assert frame["code"] == "UNKNOWN_ACTION"
    assert frame["action"] == action


def test_an_action_frame_without_a_session_id_is_invalid(
    client: TestClient, campaign: tuple[str, str]
):
    campaign_id, _ = campaign
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "end_session"})
        frame = ws.receive_json()

    assert frame["code"] == "INVALID_FRAME"


def test_an_unreachable_owner_gets_an_error_frame_not_a_success(
    game_session_upstream: str, board_state_upstream: str, monkeypatch, campaign, board, token
):
    campaign_id, session_id = campaign
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
    with TestClient(gateway_app) as down_client, _open(down_client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "move_token",
                "session_id": session_id,
                "token_id": token,
                "to_x": 2,
                "to_y": 2,
            }
        )
        frame = ws.receive_json()

    assert frame["type"] == "error"
    assert frame["code"] == "UPSTREAM_UNAVAILABLE"
    assert frame["action"] == "move_token"


def test_the_character_owner_changes_hp_and_a_stranger_is_refused(
    client: TestClient, campaign: tuple[str, str], character_sheet_upstream: str
):
    campaign_id, session_id = campaign
    _join(client, campaign_id, OTHER_PLAYER)
    created = client.post(
        "/api/v1/characters",
        json={"name": "Durable", "characterClass": "Monk"},
        headers=bearer(PLAYER),
    )
    assert created.status_code == 201, created.text
    character_id = created.json()["id"]
    before = client.get(f"/api/v1/characters/{character_id}", headers=bearer(PLAYER)).json()

    with _open(client, campaign_id, PLAYER) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "modify_hp",
                "session_id": session_id,
                "character_id": character_id,
                "delta": -3,
            }
        )
        applied = ws.receive_json()

    assert applied["status"] == "applied"
    after = client.get(f"/api/v1/characters/{character_id}", headers=bearer(PLAYER)).json()
    assert after["current_hp"] == before["current_hp"] - 3

    with _open(client, campaign_id, OTHER_PLAYER) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "modify_hp",
                "session_id": session_id,
                "character_id": character_id,
                "delta": -10,
            }
        )
        refused = ws.receive_json()

    assert refused["type"] == "error"
    assert refused["code"] == "PERMISSION_DENIED"
    assert refused["status_code"] == 403
    unchanged = client.get(f"/api/v1/characters/{character_id}", headers=bearer(PLAYER)).json()
    assert unchanged["current_hp"] == after["current_hp"]


def test_a_spectator_toggle_door_gets_the_owner_403(
    client: TestClient, campaign: tuple[str, str], board: str
):
    campaign_id, session_id = campaign
    _join(client, campaign_id, SPECTATOR, role="spectator")
    with _open(client, campaign_id, SPECTATOR) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {"action": "toggle_door", "session_id": session_id, "door_id": "door-portcullis-1"}
        )
        frame = ws.receive_json()

    assert frame["code"] == "PERMISSION_DENIED"
    assert frame["action"] == "toggle_door"
    assert frame["status_code"] == 403


def test_the_dm_places_a_light_and_a_player_gets_the_owner_403(
    client: TestClient, campaign: tuple[str, str], board: str
):
    campaign_id, session_id = campaign
    with _open(client, campaign_id, DM) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "place_light",
                "session_id": session_id,
                "light_id": "campfire_01",
                "x": 10.0,
                "y": 10.0,
                "bright_radius": 10.0,
                "dim_radius": 20.0,
            }
        )
        applied = ws.receive_json()
    assert applied["status"] == "applied"
    assert applied["light_id"] == "campfire_01"

    with _open(client, campaign_id, PLAYER) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {"action": "place_light", "session_id": session_id, "light_id": "cheat", "x": 1, "y": 1}
        )
        refused = ws.receive_json()
    assert refused["code"] == "PERMISSION_DENIED"
    assert refused["status_code"] == 403
