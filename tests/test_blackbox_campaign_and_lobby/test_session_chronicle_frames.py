"""Blackbox frontdoor tests: a token move reaches the session sockets as a chronicle line.

board_state publishes `TokenMoved` on `runefoble.events.board`. game_session records
`TokenMoveChronicled` on the session and publishes it on `runefoble.events.session`. The gateway
consumer turns it into one `chronicle_entry` frame for each session socket. The frame carries the
same entry that `GET /api/v1/sessions/{id}/events` returns. Setup runs through public routes and
the standard `TokenMoved` event. Governed by ADR-0006, ADR-0011, ADR-0015 and Hard Invariant 7.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import TokenMoved
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_evelyn"
BOARD_STREAM = "runefoble.events.board"


def _session(client_gw: TestClient, client_sess: TestClient) -> str:
    """Create a campaign and a session in it. Return the session id."""
    campaign = client_gw.post("/api/v1/campaigns", json={"title": "Moves"}, headers=bearer(DM))
    assert campaign.status_code == 201, campaign.text
    session = client_sess.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Night"},
        headers=bearer(DM),
    )
    assert session.status_code == 201, session.text
    return session.json()["id"]


def _publish_move(mock_bus: MockAsyncRedis, session_id: str, to: tuple[int, int]) -> None:
    move = TokenMoved(
        aggregate_id=UUID(session_id),
        session_id=UUID(session_id),
        token_id=f"tok-{uuid4().hex[:6]}",
        name="Valeros the Bold",
        from_x=1,
        from_y=1,
        to_x=to[0],
        to_y=to[1],
    )

    async def _send() -> None:
        await RedisStreamsEventBus(client=mock_bus).publish_event(BOARD_STREAM, move)

    asyncio.run(_send())


def test_a_token_move_gives_each_socket_one_chronicle_entry_frame(
    mock_bus: MockAsyncRedis, client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _session(client_gw, client_sess)

    with client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as dm_ws:
        assert dm_ws.receive_json()["type"] == "connected"
        _publish_move(mock_bus, session_id, (3, 3))
        frame = dm_ws.receive_json()

    feed = client_gw.get(f"/api/v1/sessions/{session_id}/events", headers=bearer(DM))
    assert feed.status_code == 200, feed.text
    (line,) = [entry for entry in feed.json() if entry["kind"] == "token_moved"]
    assert frame == {"type": "chronicle_entry", "sessionId": session_id, "entry": line}
    assert line["text"] == "Valeros the Bold moved to (3, 3)"
