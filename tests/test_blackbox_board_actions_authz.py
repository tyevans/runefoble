"""Blackbox frontdoor tests for board token, action, and WebSocket authorization (TASK-0547).

Governed by Hard Invariant 7, ADR-0001 and ADR-0014.

- Every request goes through a public HTTP route or the board WebSocket with a signed bearer.
- A board is created through `POST /api/v1/boards`. Tokens are placed through `POST .../tokens`.
  That route writes the `board_token` tuples. No test writes a `board_token` tuple.
- Campaign roles and character ownership are written on the shared SpiceDB mock. The campaign
  and character frontdoors live in other services. This is the SpiceDB process boundary.
- Assertions read HTTP and WebSocket output only.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from board_state.main import app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

DM = "dm-evelyn"
OWNER = "player-marcus"
OTHER = "player-nadia"
SPECTATOR = "spectator-iris"
STRANGER = "stranger-mallory"
MOVE = {"to_x": 3, "to_y": 2}


def bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def _write(spicedb, kind: str, rid: str, relation: str, subject_type: str, subject: str) -> None:
    asyncio.run(spicedb.write_relationship(kind, rid, relation, subject_type, subject))


def _campaign(spicedb) -> str:
    campaign_id = str(uuid4())
    for relation, user in (
        ("dungeon_master", DM),
        ("player", OWNER),
        ("player", OTHER),
        ("spectator", SPECTATOR),
    ):
        _write(spicedb, "campaign", campaign_id, relation, "user", user)
    return campaign_id


def _character(spicedb, campaign_id: str, owner: str) -> str:
    character_id = str(uuid4())
    _write(spicedb, "character", character_id, "campaign", "campaign", campaign_id)
    _write(spicedb, "character", character_id, "owner", "user", owner)
    return character_id


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def campaign(spicedb) -> str:
    return _campaign(spicedb)


@pytest.fixture
def owner_character(spicedb, campaign: str) -> str:
    return _character(spicedb, campaign, OWNER)


@pytest.fixture
def board(client: TestClient, campaign: str) -> str:
    session_id = f"t0547-{uuid4().hex}"
    res = client.post(
        "/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign, "cols": 12, "rows": 12},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return session_id


def _place(client, board, who, character_id=None, token_id="valeros", x=2, y=2):
    body = {"token_id": token_id, "name": token_id.title(), "x": x, "y": y}
    if character_id:
        body["character_id"] = character_id
    return client.post(f"/api/v1/boards/{board}/tokens", json=body, headers=bearer(who))


@pytest.fixture
def token(client: TestClient, board: str, owner_character: str) -> str:
    """The owner places a token for their character through the public route."""
    res = _place(client, board, OWNER, owner_character, token_id=f"valeros-{uuid4().hex[:8]}")
    assert res.status_code == 200, res.text
    return res.json()["token_id"]


def _pos(client: TestClient, board: str, token_id: str) -> tuple[int, int]:
    tok = client.get(f"/api/v1/boards/{board}", headers=bearer(DM)).json()["tokens"][token_id]
    return tok["x"], tok["y"]


# --- Anonymous callers -------------------------------------------------------------------------

ANONYMOUS_ROUTES = [
    ("post", "/api/v1/boards/{b}/tokens/{t}/move", MOVE),
    ("post", "/api/v1/boards/{b}/move", {"token_id": "{t}", **MOVE}),
    ("post", "/api/v1/boards/{b}/aoe/place", {"origin_x": 2, "origin_y": 2}),
    ("post", "/api/v1/boards/{b}/aoe/evaluate", {"origin_x": 2, "origin_y": 2}),
    ("post", "/api/v1/boards/{b}/tokens", {"name": "x", "x": 1, "y": 1}),
    ("delete", "/api/v1/boards/{b}/tokens/{t}", None),
    ("post", "/api/v1/boards/{b}/tokens/{t}/action", {"action": "dodge"}),
    ("post", "/api/v1/boards/{b}/physics/knockback", {"token_id": "{t}"}),
    ("post", "/api/v1/boards/{b}/physics/simulate-throw", {}),
    ("post", "/api/v1/boards/{b}/vfx/spell", {"spell_name": "x", "target_x": 1, "target_y": 1}),
    ("post", "/api/v1/boards/{b}/decals/decay", {"rounds": 1}),
    ("post", "/api/v1/boards/{b}/tokens/{t}/preview", MOVE),
    ("post", "/api/v1/board/{b}/lights", {}),
    ("post", "/api/v1/board/{b}/doors/d1/toggle", None),
]


@pytest.mark.parametrize(("method", "path", "body"), ANONYMOUS_ROUTES)
def test_anonymous_callers_are_refused_and_nothing_moves(
    client: TestClient, board: str, token: str, method: str, path: str, body
):
    payload = (
        {k: (v.replace("{t}", token) if isinstance(v, str) else v) for k, v in body.items()}
        if body is not None
        else None
    )
    res = client.request(method, path.format(b=board, t=token), json=payload)

    assert res.status_code == 401, res.text
    assert _pos(client, board, token) == (2, 2)


# --- Token placement and the board_token tuples ------------------------------------------------


def test_the_character_owner_moves_the_token_that_placement_bound_to_the_character(
    client: TestClient, board: str, token: str
):
    res = client.post(
        f"/api/v1/boards/{board}/tokens/{token}/move", json=MOVE, headers=bearer(OWNER)
    )

    assert res.status_code == 200, res.text
    assert _pos(client, board, token) == (3, 2)


@pytest.mark.parametrize("user", [OTHER, SPECTATOR, STRANGER])
def test_a_non_owner_cannot_move_the_token(client: TestClient, board: str, token: str, user: str):
    res = client.post(
        f"/api/v1/boards/{board}/tokens/{token}/move", json=MOVE, headers=bearer(user)
    )

    assert res.status_code == 403, res.text
    assert _pos(client, board, token) == (2, 2)


def test_the_dm_moves_any_token(client: TestClient, board: str, token: str):
    res = client.post(f"/api/v1/boards/{board}/tokens/{token}/move", json=MOVE, headers=bearer(DM))

    assert res.status_code == 200, res.text


def test_a_player_cannot_place_a_token_for_a_character_that_another_player_owns(
    client: TestClient, board: str, owner_character: str
):
    res = _place(client, board, OTHER, owner_character)

    assert res.status_code == 403, res.text


@pytest.mark.parametrize("user", [OWNER, SPECTATOR, STRANGER])
def test_a_token_without_a_character_needs_a_board_manager(
    client: TestClient, board: str, user: str
):
    res = _place(client, board, user)

    assert res.status_code == 403, res.text


def test_the_dm_places_a_monster_that_a_player_cannot_move(client: TestClient, board: str):
    assert _place(client, board, DM, token_id="ogre").status_code == 200

    res = client.post(f"/api/v1/boards/{board}/tokens/ogre/move", json=MOVE, headers=bearer(OWNER))

    assert res.status_code == 403, res.text


def test_a_spectator_cannot_place_a_token_for_a_character_in_the_campaign(
    client: TestClient, board: str, spicedb, campaign: str
):
    character_id = _character(spicedb, campaign, SPECTATOR)

    res = _place(client, board, SPECTATOR, character_id)

    assert res.status_code == 403, res.text


def test_a_token_id_of_another_campaign_is_refused(
    client: TestClient, board: str, token: str, spicedb
):
    other_campaign = str(uuid4())
    _write(spicedb, "campaign", other_campaign, "dungeon_master", "user", STRANGER)
    other_board = f"t0547-{uuid4().hex}"
    created = client.post(
        "/api/v1/boards",
        json={"session_id": other_board, "campaign_id": other_campaign},
        headers=bearer(STRANGER),
    )
    assert created.status_code == 200, created.text

    res = _place(client, other_board, STRANGER, token_id=token)

    assert res.status_code == 409, res.text
    still = client.post(
        f"/api/v1/boards/{board}/tokens/{token}/move", json=MOVE, headers=bearer(STRANGER)
    )
    assert still.status_code == 403, still.text


def test_a_token_id_with_unsafe_characters_is_refused(client: TestClient, board: str):
    res = _place(client, board, DM, token_id="bad id:1")

    assert res.status_code == 400, res.text


def test_removal_needs_the_owner_or_the_dm_and_frees_the_token_id(
    client: TestClient, board: str, token: str
):
    denied = client.delete(f"/api/v1/boards/{board}/tokens/{token}", headers=bearer(OTHER))
    assert denied.status_code == 403, denied.text

    removed = client.delete(f"/api/v1/boards/{board}/tokens/{token}", headers=bearer(OWNER))
    assert removed.status_code == 200, removed.text

    replaced = _place(client, board, DM, token_id=token)
    assert replaced.status_code == 200, replaced.text
    gone = client.post(
        f"/api/v1/boards/{board}/tokens/{token}/move", json=MOVE, headers=bearer(OWNER)
    )
    assert gone.status_code == 403, gone.text


# --- AoE, spells, physics, actions, previews, lights, doors ------------------------------------


def test_aoe_place_and_remove_need_campaign_play_and_evaluate_needs_board_view(
    client: TestClient, board: str
):
    body = {"origin_x": 4, "origin_y": 4, "template_id": "tpl-1"}
    base = f"/api/v1/boards/{board}/aoe"

    assert client.post(f"{base}/place", json=body, headers=bearer(SPECTATOR)).status_code == 403
    assert client.post(f"{base}/evaluate", json=body, headers=bearer(STRANGER)).status_code == 403
    assert client.post(f"{base}/evaluate", json=body, headers=bearer(SPECTATOR)).status_code == 200
    assert client.post(f"{base}/place", json=body, headers=bearer(OWNER)).status_code == 200
    assert client.delete(f"{base}/tpl-1", headers=bearer(SPECTATOR)).status_code == 403
    assert client.delete(f"{base}/tpl-1", headers=bearer(OWNER)).status_code == 200


def test_spell_vfx_needs_campaign_play_and_decal_decay_needs_a_board_manager(
    client: TestClient, board: str
):
    spell = {"spell_name": "Fireball", "target_x": 5, "target_y": 5}
    url = f"/api/v1/boards/{board}/vfx/spell"

    assert client.post(url, json=spell, headers=bearer(SPECTATOR)).status_code == 403
    assert client.post(url, json=spell, headers=bearer(OWNER)).status_code == 200
    decay = f"/api/v1/boards/{board}/decals/decay"
    assert client.post(decay, json={"rounds": 1}, headers=bearer(OWNER)).status_code == 403
    assert client.post(decay, json={"rounds": 1}, headers=bearer(DM)).status_code == 200


def test_knockback_needs_move_on_the_target_and_dice_throws_need_campaign_play(
    client: TestClient, board: str, token: str
):
    knock = f"/api/v1/boards/{board}/physics/knockback"
    throw = f"/api/v1/boards/{board}/physics/simulate-throw"

    assert client.post(knock, json={"token_id": token}, headers=bearer(OTHER)).status_code == 403
    assert client.post(knock, json={"token_id": token}, headers=bearer(OWNER)).status_code == 200
    assert client.post(throw, json={}, headers=bearer(SPECTATOR)).status_code == 403
    assert client.post(throw, json={}, headers=bearer(OWNER)).status_code == 200


def test_token_actions_need_move_on_the_acting_token(client: TestClient, board: str, token: str):
    url = f"/api/v1/boards/{board}/tokens/{token}/action"

    assert client.post(url, json={"action": "dodge"}, headers=bearer(OTHER)).status_code == 403
    assert client.post(url, json={"action": "dodge"}, headers=bearer(OWNER)).status_code == 200


def test_previews_need_board_view(client: TestClient, board: str, token: str):
    url = f"/api/v1/boards/{board}/tokens/{token}/preview"

    assert client.post(url, json=MOVE, headers=bearer(STRANGER)).status_code == 403
    assert client.post(url, json=MOVE, headers=bearer(SPECTATOR)).status_code == 200


def test_lights_need_a_board_manager_and_doors_need_campaign_play(client: TestClient, board: str):
    lights = f"/api/v1/board/{board}/lights"
    door = f"/api/v1/board/{board}/doors/missing/toggle"

    assert client.post(lights, json={}, headers=bearer(OWNER)).status_code == 403
    assert client.post(lights, json={}, headers=bearer(DM)).status_code == 200
    assert client.get(f"/boards/{board}/lights", headers=bearer(STRANGER)).status_code == 403
    assert client.post(door, headers=bearer(SPECTATOR)).status_code == 403
    assert client.post(door, headers=bearer(OWNER)).status_code != 403


def test_map_import_needs_a_board_manager(client: TestClient, board: str):
    res = client.post(f"/api/v1/boards/{board}/import/uvtt", content=b"{}", headers=bearer(OWNER))

    assert res.status_code == 403, res.text


# --- WebSocket ---------------------------------------------------------------------------------


def _connect(client: TestClient, board: str, user: str):
    return client.websocket_connect(f"/ws/boards/{board}", subprotocols=ws_subprotocols(user))


def test_a_socket_without_a_bearer_is_closed_with_1008(client: TestClient, board: str):
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(f"/ws/boards/{board}"),
    ):
        pass

    assert closed.value.code == 1008


def test_a_socket_of_a_user_without_board_view_is_closed_with_4403(client: TestClient, board: str):
    with pytest.raises(WebSocketDisconnect) as closed, _connect(client, board, STRANGER):
        pass

    assert closed.value.code == 4403


def test_a_socket_message_for_another_players_token_gets_an_error_and_the_token_stays(
    client: TestClient, board: str, token: str
):
    with _connect(client, board, OTHER) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"action": "confirm_move", "token_id": token, **MOVE})
        denied = ws.receive_json()
        ws.send_json({"action": "cancel_preview", "token_id": token})
        still_open = ws.receive_json()

    assert (denied["type"], denied["status"]) == ("error", 403)
    assert still_open["type"] == "preview_cancelled"
    assert _pos(client, board, token) == (2, 2)


def test_the_owner_socket_moves_the_token(client: TestClient, board: str, token: str):
    with _connect(client, board, OWNER) as ws:
        ws.receive_json()
        ws.send_json({"action": "confirm_move", "token_id": token, **MOVE})
        moved = ws.receive_json()

    assert moved["type"] == "token_moved"
    assert _pos(client, board, token) == (3, 2)


def test_a_spectator_socket_may_preview_but_not_act(client: TestClient, board: str, token: str):
    with _connect(client, board, SPECTATOR) as ws:
        ws.receive_json()
        ws.send_json({"action": "preview_move", "token_id": token, **MOVE})
        preview = ws.receive_json()
        ws.send_json({"action": "token_action", "token_id": token, "token_action": "dodge"})
        action = ws.receive_json()
        ws.send_json({"action": "aoe_place", "origin_x": 3, "origin_y": 3})
        aoe = ws.receive_json()
        ws.send_json(
            {"action": "cast_spell", "spell_name": "Fireball", "target_x": 3, "target_y": 3}
        )
        spell = ws.receive_json()

    assert preview["type"] == "ghost_preview"
    assert [m["status"] for m in (action, aoe, spell)] == [403, 403, 403]


def test_a_player_socket_may_place_an_aoe_and_cast_but_not_move_other_tokens(
    client: TestClient, board: str, token: str
):
    with _connect(client, board, OTHER) as ws:
        ws.receive_json()
        ws.send_json({"action": "aoe_place", "origin_x": 3, "origin_y": 3})
        aoe = ws.receive_json()
        ws.send_json(
            {"action": "cast_spell", "spell_name": "Fireball", "target_x": 3, "target_y": 3}
        )
        spell = ws.receive_json()
        ws.send_json({"action": "token_action", "token_id": token, "token_action": "dodge"})
        action = ws.receive_json()

    assert aoe["type"] == "aoe_template_placed"
    assert spell["type"] == "spell_vfx"
    assert action["status"] == 403


def test_an_unknown_socket_message_is_an_error_and_is_not_rebroadcast(
    client: TestClient, board: str
):
    with _connect(client, board, OWNER) as ws, _connect(client, board, SPECTATOR) as watcher:
        ws.receive_json()
        watcher.receive_json()
        ws.send_json({"action": "forged_dm_announcement", "text": "you win"})
        error = ws.receive_json()
        ws.send_json({"action": "cancel_preview"})
        watcher_frame = watcher.receive_json()

    assert error["code"] == "UNKNOWN_ACTION"
    assert watcher_frame["type"] == "preview_cancelled"
