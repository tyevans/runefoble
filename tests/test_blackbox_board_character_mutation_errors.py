"""Blackbox tests: board and character mutations map typed errors in one place (TASK-0752).

Governed by ADR-0015 (fail closed, no hidden errors) and Hard Invariant 7.

- A storage outage on a mutation answers 503. It never looks like a bad request (400) or a
  generic server error (500).
- Bad input still answers 400 with the domain message.
- A reference to an element that is not on the board answers 404.

Setup goes through public frontdoors only: campaign create, board create, token place, and
character create. The store double sits at the event store boundary (tests/helpers).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.main import app as board_app
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

from tests.helpers.event_store_seam import store_append_outage, store_outage
from tests.helpers.ws_identity import bearer

STORE_UNAVAILABLE = {"detail": "Event store is unavailable"}


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))


@pytest.fixture
def board(board_client: TestClient, board_campaign: str) -> str:
    """Create a 10x10 board with one token `tok-1` at (1, 1). Return the board id."""
    board_id = f"board-{uuid4().hex[:8]}"
    created = board_client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "board_id": board_id, "cols": 10, "rows": 10},
    )
    assert created.status_code == 200, created.text
    placed = board_client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "tok-1", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
    )
    assert placed.status_code == 200, placed.text
    return board_id


def test_token_move_answers_503_when_the_save_fails(board_client: TestClient, board: str):
    with store_append_outage("BoardState"):
        res = board_client.post(
            f"/api/v1/boards/{board}/tokens/tok-1/move", json={"to_x": 2, "to_y": 2}
        )

    assert res.status_code == 503, res.text
    assert res.json() == STORE_UNAVAILABLE
    kept = board_client.get(f"/api/v1/boards/{board}/tokens/tok-1")
    assert (kept.json()["x"], kept.json()["y"]) == (1, 1)


def test_token_move_answers_503_when_the_board_cannot_be_read(board_client: TestClient, board: str):
    with store_outage():
        res = board_client.post(
            f"/api/v1/boards/{board}/tokens/tok-1/move", json={"to_x": 2, "to_y": 2}
        )

    assert res.status_code == 503, res.text
    assert res.json() == STORE_UNAVAILABLE


def test_terrain_change_answers_503_when_the_save_fails(board_client: TestClient, board: str):
    with store_append_outage("BoardState"):
        res = board_client.post(
            f"/api/v1/boards/{board}/terrain",
            json={"x": 3, "y": 3, "elevation": 1, "terrain_type": "difficult"},
        )

    assert res.status_code == 503, res.text
    assert res.json() == STORE_UNAVAILABLE


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("delete", "/tokens/tok-1", None),
        ("post", "/fog-of-war/reveal", {"cells": [[5, 5]]}),
        ("post", "/tokens/tok-1/action", {"action": "dodge"}),
        (
            "post",
            "/aoe/place",
            {"shape": "sphere", "origin_x": 4, "origin_y": 4, "radius_ft": 10},
        ),
        (
            "post",
            "/physics/knockback",
            {"token_id": "tok-1", "direction_x": 1, "direction_y": 0, "distance_ft": 5},
        ),
    ],
)
def test_other_board_mutations_answer_503_when_the_save_fails(
    board_client: TestClient, board: str, method: str, path: str, body: dict | None
):
    with store_append_outage("BoardState"):
        res = board_client.request(method, f"/api/v1/boards/{board}{path}", json=body)

    assert res.status_code == 503, res.text
    assert res.json() == STORE_UNAVAILABLE


def test_a_move_out_of_bounds_is_still_a_bad_request(board_client: TestClient, board: str):
    res = board_client.post(
        f"/api/v1/boards/{board}/tokens/tok-1/move", json={"to_x": 40, "to_y": 2}
    )

    assert res.status_code == 400, res.text
    assert res.json() == {"detail": "Target coordinates (40, 2) out of bounds"}


def test_terrain_outside_the_grid_is_still_a_bad_request(board_client: TestClient, board: str):
    res = board_client.post(
        f"/api/v1/boards/{board}/terrain",
        json={"x": 30, "y": 3, "elevation": 1, "terrain_type": "difficult"},
    )

    assert res.status_code == 400, res.text
    assert "out of grid bounds" in res.json()["detail"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("delete", "/tokens/tok-1", None),
        ("post", "/tokens/tok-1/action", {"action": "dodge"}),
        (
            "post",
            "/physics/knockback",
            {"token_id": "tok-1", "direction_x": 1, "direction_y": 0, "distance_ft": 5},
        ),
    ],
)
def test_a_token_that_left_the_board_is_not_found(
    board_client: TestClient, board: str, method: str, path: str, body: dict | None
):
    removed = board_client.delete(f"/api/v1/boards/{board}/tokens/tok-1")
    assert removed.status_code == 200, removed.text

    res = board_client.request(method, f"/api/v1/boards/{board}{path}", json=body)

    assert res.status_code == 404, res.text
    assert res.json() == {"detail": "Token 'tok-1' not found on grid"}


@pytest.fixture
def character_client() -> TestClient:
    return TestClient(character_app, headers=bearer("sheet-owner"))


@pytest.fixture
def character_id(character_client: TestClient) -> str:
    res = character_client.post(
        "/api/v1/characters",
        json={"name": "Merisiel", "character_class": "Rogue", "max_hp": 20},
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


def test_character_health_change_answers_503_when_the_save_fails(
    character_client: TestClient, character_id: str
):
    with store_append_outage("CharacterSheet"):
        res = character_client.post(
            f"/api/v1/characters/{character_id}/health", json={"delta": -3, "source": "damage"}
        )

    assert res.status_code == 503, res.text
    assert res.json() == STORE_UNAVAILABLE
    kept = character_client.get(f"/api/v1/characters/{character_id}")
    assert kept.json()["current_hp"] == 20


def test_character_penalty_answers_503_when_the_save_fails(
    character_client: TestClient, character_id: str
):
    with store_append_outage("CharacterSheet"):
        res = character_client.post(
            f"/api/v1/characters/{character_id}/penalties",
            json={"penalty_type": "drunk", "description": "Ale", "imposed_by": "human_dm"},
        )

    assert res.status_code == 503, res.text
    assert res.json() == STORE_UNAVAILABLE


def test_clearing_an_inactive_penalty_is_still_a_bad_request(
    character_client: TestClient, character_id: str
):
    res = character_client.delete(f"/api/v1/characters/{character_id}/penalties/drunk")

    assert res.status_code == 400, res.text
    assert res.json() == {"detail": "Penalty 'drunk' is not active on this character"}
