"""Blackbox frontdoor tests: the session socket gets dice and turn frames from domain events.

Governed by TASK-0923, ADR-0006 (Redis Streams), ADR-0011 (events), ADR-0015 and Hard
Invariant 7. Setup runs through public routes only. The owner (game_session) publishes the
domain event, and the gateway consumer turns it into one session frame for each socket.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.shared.streams import STREAM_SESSION
from starlette.testclient import WebSocketTestSession

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_evelyn"
PLAYER = "player_marcus"


def _active_session(client_gw: TestClient, client_sess: TestClient) -> str:
    """Create a campaign and a session, seat one player, and start the session. Return its id."""
    campaign = client_gw.post("/api/v1/campaigns", json={"title": "Live"}, headers=bearer(DM))
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    invite = client_sess.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=bearer(DM)
    )
    assert invite.status_code == 201, invite.text
    redeemed = client_sess.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(PLAYER),
    )
    assert redeemed.status_code == 200, redeemed.text
    session = client_sess.post(
        f"/api/v1/campaigns/{campaign_id}/sessions", json={"title": "Night"}, headers=bearer(DM)
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["id"]
    joined = client_sess.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": str(uuid4()),
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
        headers=bearer(PLAYER),
    )
    assert joined.status_code == 200, joined.text
    started = client_gw.post(f"/api/v1/sessions/{session_id}/start", headers=bearer(DM))
    assert started.status_code == 200, started.text
    return session_id


def _connect(client_gw: TestClient, session_id: str, user: str):
    return client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols(user)
    )


def _roll(client_sess: TestClient, session_id: str, formula: str) -> dict[str, Any]:
    reply = client_sess.post(
        f"/api/v1/sessions/{session_id}/roll",
        json={"formula": formula, "roller_name": "Valeros"},
        headers=bearer(PLAYER),
    )
    assert reply.status_code == 200, reply.text
    return reply.json()


def _dice_frame(session_id: str, roll: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "dice_rolled",
        "sessionId": session_id,
        "rollerId": PLAYER,
        "rollerName": "Valeros",
        "formula": roll["formula"],
        "total": roll["total"],
        "rolls": roll["rolls"],
        "isCrit": roll["is_crit"],
        "isFumble": roll["is_fumble"],
    }


def _open_both(sockets: tuple[WebSocketTestSession, ...]) -> None:
    for socket in sockets:
        assert socket.receive_json()["type"] == "connected"


def test_a_dm_turn_advance_gives_each_socket_one_turn_advanced_frame(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _active_session(client_gw, client_sess)

    with (
        _connect(client_gw, session_id, DM) as dm_ws,
        _connect(client_gw, session_id, PLAYER) as pws,
    ):
        _open_both((dm_ws, pws))
        advanced = client_gw.post(
            f"/api/v1/sessions/{session_id}/turns/advance", headers=bearer(DM)
        )
        assert advanced.status_code == 200, advanced.text
        state = advanced.json()
        expected = {
            "type": "turn_advanced",
            "sessionId": session_id,
            "previousTurn": state["current_turn"] - 1,
            "newTurn": state["current_turn"],
            "activeCharacterId": state["active_character_id"],
        }
        assert dm_ws.receive_json() == expected
        assert pws.receive_json() == expected


def test_a_refused_turn_advance_sends_no_frame(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _active_session(client_gw, client_sess)

    with _connect(client_gw, session_id, DM) as dm_ws:
        _open_both((dm_ws,))
        refused = client_gw.post(
            f"/api/v1/sessions/{session_id}/turns/advance", headers=bearer(PLAYER)
        )
        assert refused.status_code == 403
        roll = _roll(client_sess, session_id, "1d6")
        # The next frame is the roll, so the refused advance sent nothing.
        assert dm_ws.receive_json() == _dice_frame(session_id, roll)


def test_a_dice_roll_gives_each_socket_one_dice_rolled_frame(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _active_session(client_gw, client_sess)

    with (
        _connect(client_gw, session_id, DM) as dm_ws,
        _connect(client_gw, session_id, PLAYER) as pws,
    ):
        _open_both((dm_ws, pws))
        roll = _roll(client_sess, session_id, "1d20+5")
        expected = _dice_frame(session_id, roll)
        assert dm_ws.receive_json() == expected
        assert pws.receive_json() == expected


def test_a_redelivered_dice_event_gives_no_second_frame(
    mock_bus: MockAsyncRedis, client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _active_session(client_gw, client_sess)

    with _connect(client_gw, session_id, DM) as dm_ws:
        _open_both((dm_ws,))
        first = _roll(client_sess, session_id, "1d20")
        assert dm_ws.receive_json() == _dice_frame(session_id, first)

        # Redis delivers the same stream entry again (a publisher retry or a reclaim).
        _entry_id, fields = next(
            (entry_id, fields)
            for entry_id, fields in reversed(mock_bus.streams[STREAM_SESSION])
            if fields["event_type"] == "runefoble.events.dice.rolled"
        )
        asyncio.run(mock_bus.xadd(STREAM_SESSION, dict(fields)))

        second = _roll(client_sess, session_id, "2d8")
        assert dm_ws.receive_json() == _dice_frame(session_id, second)


def test_a_dice_roll_in_another_session_reaches_only_that_session(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_a = _active_session(client_gw, client_sess)
    session_b = _active_session(client_gw, client_sess)

    with _connect(client_gw, session_a, DM) as ws_a:
        _open_both((ws_a,))
        _roll(client_sess, session_b, "1d4")
        roll_a = _roll(client_sess, session_a, "1d12")
        assert ws_a.receive_json() == _dice_frame(session_a, roll_a)


def test_the_gateway_reports_the_session_frame_consumer_on_healthz(client_gw: TestClient) -> None:
    health = client_gw.get("/healthz")
    assert health.status_code == 200
    assert health.json()["consumers"] == {"session_frames": "running"}
