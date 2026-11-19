"""Blackbox frontdoor tests for the board owner routes the campaign socket relays (TASK-0846 part a).

Each test calls the route through `runefoble_platform.service_client.owner_routes`, so the
table entry is covered too. A DM succeeds. A caller without the owner permission gets 403.
The owner publishes its own domain event, which the test reads from the Redis Stream.
Setup uses only public routes (ADR-0014, Hard Invariant 7).
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_platform.service_client import owner_routes

from tests.helpers.campaign_setup import add_member, create_dm_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer
from tests.test_blackbox_uvtt_doors_lights.test_uvtt_doors_frontdoor import build_uvtt_with_doors

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_owner_board"
PLAYER = "player_owner_board"
SPECTATOR = "spectator_owner_board"


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app)


@pytest.fixture
def character_client() -> TestClient:
    return TestClient(character_app)


def _published(mock_bus: MockAsyncRedis, event_type: str) -> list[dict]:
    payloads: list[dict] = []
    for entries in mock_bus.streams.values():
        for _entry_id, fields in entries:
            if fields.get("event_type") == event_type:
                payloads.append(json.loads(fields["payload"]))
    return payloads


@pytest.fixture
def campaign_with_board(board_client: TestClient) -> tuple[str, str]:
    """A campaign with a player and a spectator, and a board on it. The DM owns both."""
    campaign_id = create_dm_campaign(DM)
    add_member(campaign_id, DM, PLAYER, "player")
    add_member(campaign_id, DM, SPECTATOR, "spectator")
    board_id = f"board-owner-{uuid4().hex[:8]}"
    created = board_client.post(
        "/api/v1/boards",
        json={"session_id": board_id, "campaign_id": campaign_id},
        headers=bearer(DM),
    )
    assert created.status_code == 200, created.text
    return campaign_id, board_id


def _request(client: TestClient, route, who: str, json_body=None):
    return client.request(route.method, route.path, headers=bearer(who), json=json_body)


def test_dm_toggles_door_and_owner_publishes_door_toggled(
    board_client: TestClient, mock_bus: MockAsyncRedis, campaign_with_board
) -> None:
    _campaign_id, board_id = campaign_with_board
    imported = board_client.post(
        f"/api/v1/boards/{board_id}/import/uvtt", json=build_uvtt_with_doors(), headers=bearer(DM)
    )
    assert imported.status_code == 200, imported.text

    route = owner_routes.toggle_door(board_id, "main_gate")
    res = _request(board_client, route, DM)

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "success"
    assert _published(mock_bus, "runefoble.events.board.door_toggled")


def test_spectator_cannot_toggle_door(
    board_client: TestClient, mock_bus: MockAsyncRedis, campaign_with_board
) -> None:
    _campaign_id, board_id = campaign_with_board
    board_client.post(
        f"/api/v1/boards/{board_id}/import/uvtt", json=build_uvtt_with_doors(), headers=bearer(DM)
    )
    before = len(_published(mock_bus, "runefoble.events.board.door_toggled"))

    res = _request(board_client, owner_routes.toggle_door(board_id, "main_gate"), SPECTATOR)

    assert res.status_code == 403, res.text
    assert len(_published(mock_bus, "runefoble.events.board.door_toggled")) == before


def test_dm_places_light_and_owner_publishes_light_placed(
    board_client: TestClient, mock_bus: MockAsyncRedis, campaign_with_board
) -> None:
    _campaign_id, board_id = campaign_with_board

    res = _request(
        board_client,
        owner_routes.place_light(board_id),
        DM,
        {"light_id": f"torch-{uuid4().hex[:6]}", "x": 3.0, "y": 4.0},
    )

    assert res.status_code == 200, res.text
    assert _published(mock_bus, "runefoble.events.board.light_source_placed")


def test_player_cannot_place_light(
    board_client: TestClient, mock_bus: MockAsyncRedis, campaign_with_board
) -> None:
    _campaign_id, board_id = campaign_with_board
    before = len(_published(mock_bus, "runefoble.events.board.light_source_placed"))

    res = _request(
        board_client,
        owner_routes.place_light(board_id),
        PLAYER,
        {"light_id": "torch-denied", "x": 1.0, "y": 1.0},
    )

    assert res.status_code == 403, res.text
    assert len(_published(mock_bus, "runefoble.events.board.light_source_placed")) == before


def test_dm_places_monster_token(
    board_client: TestClient, mock_bus: MockAsyncRedis, campaign_with_board
) -> None:
    _campaign_id, board_id = campaign_with_board
    token_id = f"goblin-{uuid4().hex[:6]}"

    route = owner_routes.place_token(board_id)
    res = _request(
        board_client,
        route,
        DM,
        {"token_id": token_id, "name": "Goblin", "token_type": "monster", "x": 2, "y": 2},
    )

    assert res.status_code == 200, res.text
    assert res.json()["token_type"] == "monster"
    assert _published(mock_bus, "runefoble.events.board.token_placed")


def test_player_cannot_place_monster_token_bound_to_own_character(
    board_client: TestClient,
    character_client: TestClient,
    mock_bus: MockAsyncRedis,
    campaign_with_board,
) -> None:
    """A player may place a PC token for a character they edit. A monster token needs the DM."""
    _campaign_id, board_id = campaign_with_board
    created = character_client.post(
        "/api/v1/characters",
        json={
            "name": "Merisiel",
            "character_class": "Rogue 3",
            "max_hp": 24,
            "armor_class": 16,
            "speed": 30,
        },
        headers=bearer(PLAYER),
    )
    assert created.status_code == 200, created.text
    character_id = created.json()["character_id"]
    before = len(_published(mock_bus, "runefoble.events.board.token_placed"))

    pc = _request(
        board_client,
        owner_routes.place_token(board_id),
        PLAYER,
        {"name": "Merisiel", "token_type": "pc", "x": 1, "y": 1, "character_id": character_id},
    )
    assert pc.status_code == 200, pc.text

    monster = _request(
        board_client,
        owner_routes.place_token(board_id),
        PLAYER,
        {
            "name": "Ogre",
            "token_type": "monster",
            "x": 5,
            "y": 5,
            "character_id": character_id,
        },
    )

    assert monster.status_code == 403, monster.text
    assert len(_published(mock_bus, "runefoble.events.board.token_placed")) == before + 1
