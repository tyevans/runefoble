"""Blackbox frontdoor tests: a Watcher whisper reaches only the DM session sockets.

Governed by TASK-0927, ADR-0001 (SpiceDB), ADR-0011 (events), ADR-0015 (fail loud) and Hard
Invariant 7. Setup runs through public routes only. The Watcher publishes `WhisperRecorded`
after the save. The gateway consumer turns it into one `dm_whisper` frame for each socket whose
caller holds `session.control`. Player and spectator sockets never get the frame.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_platform.event_deserializer import deserialize_event
from starlette.testclient import WebSocketTestSession

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.the_watcher_app import app_with_container, fresh_store_container
from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_evelyn"
PLAYER = "player_marcus"
SPECTATOR = "spectator_sol"
WATCHER_STREAM = "runefoble.events.watcher"
WHISPER_RECORDED = "runefoble.events.watcher.whisper_recorded"


class FailingRedis(MockAsyncRedis):
    """Redis double whose stream writes always fail, as when the broker is unreachable."""

    async def xadd(self, *args, **kwargs):
        raise ConnectionError("redis unavailable (test double)")


@pytest.fixture
def client_watcher(trusted_ws_issuer) -> TestClient:
    """The Watcher over empty stores, served without its lifespan (no narration consumer)."""
    return TestClient(app_with_container(fresh_store_container()))


def _join(client_sess: TestClient, campaign_id: str, user: str, role: str) -> None:
    invite = client_sess.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": role}, headers=bearer(DM)
    )
    assert invite.status_code == 201, invite.text
    redeemed = client_sess.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(user),
    )
    assert redeemed.status_code == 200, redeemed.text


def _table(client_gw: TestClient, client_sess: TestClient) -> tuple[str, str]:
    """Create a campaign with a player and a spectator, and an active session. Return the ids."""
    campaign = client_gw.post("/api/v1/campaigns", json={"title": "Hush"}, headers=bearer(DM))
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    _join(client_sess, campaign_id, PLAYER, "player")
    _join(client_sess, campaign_id, SPECTATOR, "spectator")
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
    return campaign_id, session_id


def _connect(client_gw: TestClient, session_id: str, user: str):
    return client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols(user)
    )


def _opened(*sockets: WebSocketTestSession) -> None:
    for socket in sockets:
        assert socket.receive_json()["type"] == "connected"


def _whisper(
    client_watcher: TestClient, campaign_id: str, session_id: str, content: str
) -> dict[str, Any]:
    reply = client_watcher.post(
        "/api/v1/watcher/whispers",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "whisper_type": "narrative_secret",
            "content": content,
        },
        headers=bearer(DM),
    )
    assert reply.status_code == 200, reply.text
    return reply.json()


def _roll(client_sess: TestClient, session_id: str) -> int:
    reply = client_sess.post(
        f"/api/v1/sessions/{session_id}/roll",
        json={"formula": "1d20", "roller_name": "Valeros"},
        headers=bearer(PLAYER),
    )
    assert reply.status_code == 200, reply.text
    return reply.json()["total"]


def _whisper_frame(session_id: str, whisper: dict[str, Any]) -> dict[str, Any]:
    return {"type": "dm_whisper", "sessionId": session_id, "whisper": whisper}


def test_a_whisper_through_the_watcher_route_publishes_the_event(
    mock_bus: MockAsyncRedis,
    client_gw: TestClient,
    client_sess: TestClient,
    client_watcher: TestClient,
) -> None:
    campaign_id, session_id = _table(client_gw, client_sess)

    whisper = _whisper(client_watcher, campaign_id, session_id, "The idol is a fake.")

    recorded = [
        deserialize_event(fields)
        for _id, fields in mock_bus.streams.get(WATCHER_STREAM, [])
        if fields["event_type"] == WHISPER_RECORDED
    ]
    assert [event.whisper for event in recorded] == [whisper]


def test_only_the_dm_socket_gets_the_dm_whisper_frame(
    client_gw: TestClient, client_sess: TestClient, client_watcher: TestClient
) -> None:
    campaign_id, session_id = _table(client_gw, client_sess)

    with (
        _connect(client_gw, session_id, DM) as dm_ws,
        _connect(client_gw, session_id, PLAYER) as player_ws,
        _connect(client_gw, session_id, SPECTATOR) as spectator_ws,
    ):
        _opened(dm_ws, player_ws, spectator_ws)
        whisper = _whisper(client_watcher, campaign_id, session_id, "The idol is a fake.")
        assert dm_ws.receive_json() == _whisper_frame(session_id, whisper)

        # The gateway sent the whisper before the roll exists, so a leaked whisper frame would
        # come before the roll frame on the other sockets.
        total = _roll(client_sess, session_id)
        assert dm_ws.receive_json()["total"] == total
        # The next frame of the player and the spectator is the roll, so no whisper reached them.
        for socket in (player_ws, spectator_ws):
            frame = socket.receive_json()
            assert frame["type"] == "dice_rolled"
            assert frame["total"] == total


def test_a_redelivered_whisper_event_gives_no_second_frame(
    mock_bus: MockAsyncRedis,
    client_gw: TestClient,
    client_sess: TestClient,
    client_watcher: TestClient,
) -> None:
    campaign_id, session_id = _table(client_gw, client_sess)

    with _connect(client_gw, session_id, DM) as dm_ws:
        _opened(dm_ws)
        first = _whisper(client_watcher, campaign_id, session_id, "First secret.")
        assert dm_ws.receive_json() == _whisper_frame(session_id, first)

        # Redis delivers the same stream entry again (a publisher retry or a reclaim).
        fields = next(
            fields
            for _id, fields in reversed(mock_bus.streams[WATCHER_STREAM])
            if fields["event_type"] == WHISPER_RECORDED
        )
        asyncio.run(mock_bus.xadd(WATCHER_STREAM, dict(fields)))

        second = _whisper(client_watcher, campaign_id, session_id, "Second secret.")
        assert dm_ws.receive_json() == _whisper_frame(session_id, second)


def test_an_unreachable_stream_answers_503_on_the_whisper_route(
    use_redis_client, client_gw: TestClient, client_sess: TestClient, client_watcher: TestClient
) -> None:
    campaign_id, session_id = _table(client_gw, client_sess)

    use_redis_client(FailingRedis())
    reply = client_watcher.post(
        "/api/v1/watcher/whispers",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "whisper_type": "narrative_secret",
            "content": "Nobody hears this.",
        },
        headers=bearer(DM),
    )

    assert reply.status_code == 503
    assert reply.json()["event_type"] == WHISPER_RECORDED
