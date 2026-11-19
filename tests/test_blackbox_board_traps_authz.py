"""Blackbox frontdoor tests for board traps, the secret layer, and board creation (TASK-0546).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), ADR-0001 and ADR-0014.

- Requests go through the public HTTP routes and the board WebSocket with signed bearer tokens.
- A board is created through `POST /api/v1/boards`. That route writes the board tuple.
- Campaign roles are written on the shared SpiceDB mock, which is the SpiceDB process boundary.
  The campaign frontdoor lives in the gateway. These tests start the board service alone.
- Assertions read HTTP and WebSocket output only.
"""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest
from board_state.main import app
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzSchemaError, AuthzUnavailableError, AuthzWriteError

from tests.helpers.campaign_setup import add_member, create_dm_campaign
from tests.helpers.ws_identity import bearer, ws_subprotocols

DM = "dm-evelyn"
PLAYER = "player-marcus"
SPECTATOR = "spectator-iris"
STRANGER = "stranger-mallory"
SECRET_NAME = "Obsidian Fang Pit"
SECRET_TEXT = "Poisoned spikes under the rug in the throne room"
SECRET_PAYLOAD_KEY = "venom_grade_omega"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def campaign(trusted_ws_issuer) -> str:
    """A campaign with a DM, a player and a spectator. The stranger holds no role."""
    campaign_id = create_dm_campaign(DM)
    add_member(campaign_id, DM, PLAYER, "player")
    add_member(campaign_id, DM, SPECTATOR, "spectator")
    return campaign_id


@pytest.fixture
def player_character(spicedb, campaign: str) -> str:
    """A character that the player owns in the campaign. Character creation lives in another service."""
    character_id = str(uuid4())
    for relation, subject_type, subject_id in (
        ("campaign", "campaign", campaign),
        ("owner", "user", PLAYER),
    ):
        asyncio.run(
            spicedb.write_relationship(
                resource_type="character",
                resource_id=character_id,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
            )
        )
    return character_id


@pytest.fixture
def board(client: TestClient, campaign: str) -> str:
    """A board that the DM creates through the public route. Returns its session id."""
    session_id = f"t0546-{uuid4().hex}"
    created = client.post(
        "/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign, "cols": 12, "rows": 12},
        headers=bearer(DM),
    )
    assert created.status_code == 200, created.text
    return session_id


@pytest.fixture
def secret_trap(client: TestClient, board: str) -> str:
    """A secret trap at (4, 3) that the DM places. Returns its id."""
    res = client.post(
        f"/api/v1/boards/{board}/traps",
        json={
            "name": SECRET_NAME,
            "x": 4,
            "y": 3,
            "is_secret": True,
            "description": SECRET_TEXT,
            "damage_dice": "2d6",
            "effect_payload": {SECRET_PAYLOAD_KEY: 9},
        },
        headers=bearer(DM),
    )
    assert res.status_code == 201, res.text
    return res.json()["trap_id"]


def _assert_no_secret(text: str, trap_id: str) -> None:
    for secret in (trap_id, SECRET_NAME, SECRET_TEXT, SECRET_PAYLOAD_KEY):
        assert secret not in text, f"secret layer data '{secret}' reached a non-DM caller"


# --- Board creation -------------------------------------------------------------------------


def test_anonymous_board_creation_is_refused(client: TestClient, campaign: str):
    res = client.post("/api/v1/boards", json={"session_id": "x", "campaign_id": campaign})

    assert res.status_code == 401, res.text


def test_board_creation_without_campaign_is_a_bad_request(client: TestClient):
    res = client.post("/api/v1/boards", json={"session_id": "no-campaign"}, headers=bearer(DM))

    assert res.status_code == 400, res.text


@pytest.mark.parametrize("user", [PLAYER, SPECTATOR, STRANGER])
def test_board_creation_needs_run_session_on_the_campaign(
    client: TestClient, campaign: str, user: str
):
    res = client.post(
        "/api/v1/boards",
        json={"session_id": f"denied-{uuid4().hex}", "campaign_id": campaign},
        headers=bearer(user),
    )

    assert res.status_code == 403, res.text


def test_creating_an_existing_board_does_not_rebind_it_to_another_campaign(
    client: TestClient, board: str
):
    """A DM of another campaign cannot take over a board by creating its session id again."""
    other_campaign = create_dm_campaign(STRANGER)

    again = client.post(
        "/api/v1/boards",
        json={"session_id": board, "campaign_id": other_campaign},
        headers=bearer(STRANGER),
    )
    assert again.status_code == 409, again.text

    takeover = client.post(
        f"/api/v1/boards/{board}/switch-map",
        json={"new_map_id": "stolen"},
        headers=bearer(STRANGER),
    )
    assert takeover.status_code == 403, takeover.text


def test_failed_board_tuple_write_returns_503(
    client: TestClient, campaign: str, spicedb, monkeypatch
):
    async def refuse_write(**_kwargs):
        raise AuthzWriteError("SpiceDB did not apply the relationship write")

    monkeypatch.setattr(spicedb, "write_relationship", refuse_write)

    res = client.post(
        "/api/v1/boards",
        json={"session_id": f"write-fail-{uuid4().hex}", "campaign_id": campaign},
        headers=bearer(DM),
    )

    assert res.status_code == 503, res.text


# --- Secret layer on reads --------------------------------------------------------------------


def test_anonymous_board_read_is_refused(client: TestClient, board: str, secret_trap: str):
    res = client.get(f"/api/v1/boards/{board}")

    assert res.status_code == 401, res.text
    _assert_no_secret(res.text, secret_trap)


@pytest.mark.parametrize("user", [PLAYER, SPECTATOR])
def test_board_read_hides_the_secret_trap_from_non_dm(
    client: TestClient, board: str, secret_trap: str, user: str
):
    res = client.get(f"/api/v1/boards/{board}", headers=bearer(user))

    assert res.status_code == 200, res.text
    _assert_no_secret(res.text, secret_trap)
    assert res.json()["traps"] == {}


def test_board_read_refuses_a_stranger_without_returning_board_data(
    client: TestClient, board: str, secret_trap: str
):
    res = client.get(f"/api/v1/boards/{board}", headers=bearer(STRANGER))

    assert res.status_code == 403, res.text
    _assert_no_secret(res.text, secret_trap)
    assert "tokens" not in res.json()


def test_board_read_shows_the_secret_trap_to_the_dm(
    client: TestClient, board: str, secret_trap: str
):
    res = client.get(f"/api/v1/boards/{board}", headers=bearer(DM))

    assert res.status_code == 200, res.text
    trap = res.json()["traps"][secret_trap]
    assert trap["name"] == SECRET_NAME
    assert trap["description"] == SECRET_TEXT


def test_trap_list_hides_the_secret_trap_from_a_player(
    client: TestClient, board: str, secret_trap: str
):
    player = client.get(f"/api/v1/boards/{board}/traps", headers=bearer(PLAYER))
    dm = client.get(f"/api/v1/boards/{board}/traps", headers=bearer(DM))

    assert player.status_code == 200, player.text
    assert player.json()["total"] == 0
    _assert_no_secret(player.text, secret_trap)
    assert [t["trap_id"] for t in dm.json()["traps"]] == [secret_trap]


def test_a_sprung_secret_trap_reaches_a_player_without_its_dm_notes(
    client: TestClient, board: str, secret_trap: str, player_character: str
):
    """A sprung trap is revealed. Its place stays. Its description, payload and DC do not."""
    placed = client.post(
        f"/api/v1/boards/{board}/tokens",
        json={
            "token_id": "valeros",
            "name": "Valeros",
            "x": 2,
            "y": 3,
            "is_friendly": True,
            "character_id": player_character,
        },
        headers=bearer(PLAYER),
    )
    assert placed.status_code == 200, placed.text
    moved = client.post(
        f"/api/v1/boards/{board}/tokens/valeros/move",
        json={"to_x": 6, "to_y": 3},
        headers=bearer(PLAYER),
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["trap_triggered"] == secret_trap

    res = client.get(f"/api/v1/boards/{board}", headers=bearer(PLAYER))

    assert res.status_code == 200, res.text
    revealed = res.json()["traps"][secret_trap]
    assert (revealed["x"], revealed["y"], revealed["is_sprung"]) == (4, 3, True)
    for secret in (SECRET_TEXT, SECRET_PAYLOAD_KEY):
        assert secret not in res.text
    assert revealed["description"] == ""
    assert revealed["effect_payload"] == {}
    assert revealed["damage_dice"] is None
    assert res.json()["last_trap_sprung"] is None


# --- Trap and map-switch actions --------------------------------------------------------------


def test_anonymous_disarm_is_refused(client: TestClient, board: str, secret_trap: str):
    res = client.post(f"/api/v1/boards/{board}/traps/{secret_trap}/disarm")

    assert res.status_code == 401, res.text


@pytest.mark.parametrize("user", [PLAYER, SPECTATOR, STRANGER])
def test_non_dm_cannot_disarm_or_create_traps(
    client: TestClient, board: str, secret_trap: str, user: str
):
    disarm = client.post(f"/api/v1/boards/{board}/traps/{secret_trap}/disarm", headers=bearer(user))
    create = client.post(
        f"/api/v1/boards/{board}/traps", json={"x": 1, "y": 1}, headers=bearer(user)
    )

    assert disarm.status_code == 403, disarm.text
    assert create.status_code == 403, create.text
    dm_view = client.get(f"/api/v1/boards/{board}/traps", headers=bearer(DM)).json()
    assert dm_view["total"] == 1
    assert dm_view["traps"][0]["is_disarmed"] is False


def test_dm_can_disarm_a_trap(client: TestClient, board: str, secret_trap: str):
    res = client.post(f"/api/v1/boards/{board}/traps/{secret_trap}/disarm", headers=bearer(DM))

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "disarmed"


def test_switch_map_is_refused_for_anonymous_and_player_and_allowed_for_dm(
    client: TestClient, board: str
):
    body = {"new_map_id": "crypt-level-2", "cols": 14, "rows": 14}
    url = f"/api/v1/boards/{board}/switch-map"

    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers=bearer(PLAYER)).status_code == 403
    allowed = client.post(url, json=body, headers=bearer(DM))
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["new_map_id"] == "crypt-level-2"


# --- Visibility, fog, and terrain -------------------------------------------------------------


def _place_hidden_goblin(client: TestClient, board: str) -> None:
    for token in (
        {"token_id": "valeros", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
        {"token_id": "goblin", "name": "Goblin", "x": 10, "y": 10, "is_friendly": False},
    ):
        res = client.post(f"/api/v1/boards/{board}/tokens", json=token, headers=bearer(DM))
        assert res.status_code == 200, res.text


def _token_ids(visibility_response) -> set[str]:
    return {t["token_id"] for t in visibility_response.json()["tokens"]}


def test_a_player_cannot_claim_dm_visibility(client: TestClient, board: str):
    _place_hidden_goblin(client, board)

    claimed = client.get(f"/api/v1/boards/{board}/visibility?is_dm=true", headers=bearer(PLAYER))
    dm = client.get(f"/api/v1/boards/{board}/visibility", headers=bearer(DM))

    assert claimed.status_code == 200, claimed.text
    assert _token_ids(claimed) == {"valeros"}
    assert _token_ids(dm) == {"valeros", "goblin"}


@pytest.mark.parametrize("action", ["reveal", "shroud"])
def test_fog_changes_need_the_secret_layer_permission(client: TestClient, board: str, action: str):
    _place_hidden_goblin(client, board)
    url = f"/api/v1/boards/{board}/fog-of-war/{action}"
    body = {"cells": [[10, 10]]}

    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers=bearer(PLAYER)).status_code == 403
    allowed = client.post(url, json=body, headers=bearer(DM))
    assert allowed.status_code == 200, allowed.text
    assert "goblin" in _token_ids(allowed)


def test_terrain_changes_need_manage_traps(client: TestClient, board: str):
    url = f"/api/v1/boards/{board}/terrain"
    body = {"x": 2, "y": 2, "elevation": 1, "terrain_type": "rubble"}

    assert client.post(url, json=body, headers=bearer(PLAYER)).status_code == 403
    allowed = client.post(url, json=body, headers=bearer(DM))
    assert allowed.status_code == 200, allowed.text


# --- Secret portals ---------------------------------------------------------------------------


def _uvtt_with_secret_door() -> dict:
    def portal(portal_id: str, x: float, secret: bool) -> dict:
        return {
            "id": portal_id,
            "position": {"x": x, "y": 2.0},
            "bounds": [{"x": x - 0.5, "y": 2.0}, {"x": x + 0.5, "y": 2.0}],
            "closed": True,
            "locked": False,
            "secret": secret,
        }

    return {
        "format": 0.2,
        "resolution": {
            "map_origin": {"x": 0, "y": 0},
            "map_size": {"x": 12, "y": 12},
            "pixels_per_grid": 70,
        },
        "line_of_sight": [],
        "portals": [portal("main_gate", 5.0, False), portal("hidden_vault", 8.0, True)],
    }


def test_secret_doors_and_portals_reach_only_the_dm(client: TestClient, board: str):
    imported = client.post(
        f"/api/v1/boards/{board}/import/uvtt", json=_uvtt_with_secret_door(), headers=bearer(DM)
    )
    assert imported.status_code == 200, imported.text
    assert "hidden_vault" in imported.text

    for url in (f"/api/v1/boards/{board}", f"/boards/{board}/doors"):
        player = client.get(url, headers=bearer(PLAYER))
        dm = client.get(url, headers=bearer(DM))
        assert player.status_code == 200, player.text
        assert "hidden_vault" not in player.text
        assert "main_gate" in player.text
        assert "hidden_vault" in dm.text


# --- WebSocket broadcast ----------------------------------------------------------------------


def test_board_websocket_broadcasts_never_carry_the_secret_layer(
    client: TestClient, board: str, secret_trap: str, player_character: str
):
    """A player socket that sees a trap spring receives no secret trap data in any frame."""
    placed = client.post(
        f"/api/v1/boards/{board}/tokens",
        json={
            "token_id": "valeros",
            "name": "Valeros",
            "x": 2,
            "y": 3,
            "is_friendly": True,
            "character_id": player_character,
        },
        headers=bearer(PLAYER),
    )
    assert placed.status_code == 200, placed.text

    frames: list[dict] = []
    with client.websocket_connect(
        f"/ws/boards/{board}", subprotocols=ws_subprotocols(PLAYER)
    ) as player_socket:
        frames.append(player_socket.receive_json())
        player_socket.send_json(
            {"action": "confirm_move", "token_id": "valeros", "to_x": 6, "to_y": 3}
        )
        frames.append(player_socket.receive_json())
        player_socket.send_json(
            {"action": "preview_move", "token_id": "valeros", "to_x": 8, "to_y": 3}
        )
        frames.append(player_socket.receive_json())

    assert [f["type"] for f in frames][:2] == ["connected", "token_moved"]
    _assert_no_secret(json.dumps(frames), secret_trap)


# --- SpiceDB failure --------------------------------------------------------------------------


def test_spicedb_outage_returns_503_not_a_denial(
    client: TestClient, board: str, spicedb, monkeypatch
):
    async def unreachable(**_kwargs):
        raise AuthzUnavailableError("SpiceDB did not answer")

    monkeypatch.setattr(spicedb, "check_permission", unreachable)

    for res in (
        client.post(
            f"/api/v1/boards/{board}/switch-map", json={"new_map_id": "m"}, headers=bearer(DM)
        ),
        client.get(f"/api/v1/boards/{board}", headers=bearer(DM)),
    ):
        assert res.status_code == 503, res.text
        assert res.json() == {"error": "authorization_unavailable"}


def test_spicedb_schema_error_returns_500_with_an_error_id(
    client: TestClient, board: str, spicedb, monkeypatch
):
    async def schema_error(**_kwargs):
        raise AuthzSchemaError("permission not in schema")

    monkeypatch.setattr(spicedb, "check_permission", schema_error)

    res = client.post(
        f"/api/v1/boards/{board}/switch-map", json={"new_map_id": "m"}, headers=bearer(DM)
    )

    assert res.status_code == 500, res.text
    assert res.json()["error"] == "authorization_schema_error"
    assert res.json()["error_id"]
