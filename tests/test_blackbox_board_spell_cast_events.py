"""Blackbox tests: a board spell cast publishes its domain events to the board stream (TASK-0834).

Governed by ADR-0006 (Redis Streams Event Bus), ADR-0011 (eventsource-py), and Hard Invariant 7
(blackbox frontdoor tests). Casts enter through the public REST route and the public board
WebSocket. Results are read from the board stream that the bus writes.
Verifies:
- A REST cast publishes one SpellCast, and one AreaEffectExploded for an area spell.
- A WebSocket cast publishes the same events as the REST cast.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer, ws_subprotocols

BOARD_STREAM = "runefoble.events.board"
SPELL_CAST_TYPE = "runefoble.events.board.spell_cast"
AREA_EFFECT_TYPE = "runefoble.events.board.area_effect_exploded"
DM = "user-test"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def board_campaign(trusted_ws_issuer) -> str:
    """The campaign that every board in this module belongs to. `user-test` runs it."""
    return create_dm_campaign(DM)


def _board_events(redis: MockAsyncRedis, event_type: str) -> list[dict]:
    """Return the payloads of every board-stream entry with the given event type."""
    return [
        json.loads(fields["payload"])
        for _entry_id, fields in redis.streams.get(BOARD_STREAM, [])
        if fields.get("event_type") == event_type
    ]


def _open_board(client: TestClient, campaign_id: str) -> str:
    """Create a board through the public POST frontdoor and return its session id."""
    session_id = f"board-cast-{uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": 18, "rows": 14},
    )
    assert res.status_code == 200, res.text
    return session_id


def test_rest_single_target_cast_publishes_spell_cast(
    mock_bus: MockAsyncRedis, board_campaign: str
) -> None:
    """A REST cast with no radius publishes one SpellCast and no AreaEffectExploded."""
    client = TestClient(board_app, headers=bearer(DM))
    session_id = _open_board(client, board_campaign)

    res = client.post(
        f"/api/v1/boards/{session_id}/spells/cast",
        json={
            "spell_name": "Magic Missile",
            "spell_archetype": "evocation",
            "target_x": 5,
            "target_y": 5,
            "radius_ft": 0,
        },
    )
    assert res.status_code == 200, res.text

    casts = _board_events(mock_bus, SPELL_CAST_TYPE)
    assert len(casts) == 1
    assert casts[0]["spell_name"] == "Magic Missile"
    assert (casts[0]["target_x"], casts[0]["target_y"]) == (5, 5)
    assert _board_events(mock_bus, AREA_EFFECT_TYPE) == []


def test_rest_area_cast_publishes_spell_cast_and_area_effect(
    mock_bus: MockAsyncRedis, board_campaign: str
) -> None:
    """A REST area cast publishes one SpellCast and one AreaEffectExploded."""
    client = TestClient(board_app, headers=bearer(DM))
    session_id = _open_board(client, board_campaign)

    res = client.post(
        f"/api/v1/boards/{session_id}/spells/cast",
        json={
            "spell_name": "Fireball",
            "spell_archetype": "evocation",
            "target_x": 8,
            "target_y": 6,
            "radius_ft": 20,
            "damage_dice": "8d6",
            "damage_type": "fire",
        },
    )
    assert res.status_code == 200, res.text

    casts = _board_events(mock_bus, SPELL_CAST_TYPE)
    blooms = _board_events(mock_bus, AREA_EFFECT_TYPE)
    assert len(casts) == 1
    assert casts[0]["spell_name"] == "Fireball"
    assert len(blooms) == 1
    assert (blooms[0]["center_x"], blooms[0]["center_y"]) == (8, 6)
    assert blooms[0]["spell_name"] == "Fireball"


def test_socket_area_cast_publishes_spell_cast_and_area_effect(
    mock_bus: MockAsyncRedis, board_campaign: str
) -> None:
    """A cast_spell frame on the board socket publishes the same events as the REST cast."""
    client = TestClient(board_app, headers=bearer(DM))
    session_id = _open_board(client, board_campaign)

    with TestClient(board_app).websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json(
            {
                "action": "cast_spell",
                "spell_name": "Fireball",
                "spell_archetype": "evocation",
                "target_x": 9,
                "target_y": 7,
                "radius_ft": 20,
            }
        )
        frame = ws.receive_json()

    assert frame["type"] == "spell_vfx"
    casts = _board_events(mock_bus, SPELL_CAST_TYPE)
    blooms = _board_events(mock_bus, AREA_EFFECT_TYPE)
    assert len(casts) == 1
    assert casts[0]["spell_name"] == "Fireball"
    assert len(blooms) == 1
    assert (blooms[0]["center_x"], blooms[0]["center_y"]) == (9, 7)
