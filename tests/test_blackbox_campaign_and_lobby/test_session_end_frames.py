"""Blackbox frontdoor tests: the DM ends a session and every session socket gets `session_ended`.

Governed by TASK-0953, ADR-0011, ADR-0014, ADR-0015 and Hard Invariant 7. Setup runs through
public gateway and game_session routes only. The gateway end route is the only source of the
`session_ended` frame, and the frame goes to every socket of the session.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM = "dm_ends_session"
PLAYER = "player_ends_session"


def _session(client_gw: TestClient, client_sess: TestClient, *, start: bool) -> str:
    """Create a campaign with one seated player and return its session id. Start it when asked."""
    campaign = client_gw.post("/api/v1/campaigns", json={"title": "Last Night"}, headers=bearer(DM))
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
    sessions = client_gw.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(DM))
    session_id = str(sessions.json()[0]["id"])
    seated = client_sess.post(
        f"/api/v1/sessions/{session_id}/join",
        json={"character_id": str(uuid4()), "character_name": "Mira", "character_class": "Ranger"},
        headers=bearer(PLAYER),
    )
    assert seated.status_code == 200, seated.text
    if start:
        started = client_gw.post(f"/api/v1/sessions/{session_id}/start", headers=bearer(DM))
        assert started.status_code == 200, started.text
    return session_id


def _connect(client_gw: TestClient, session_id: str, user: str):
    return client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols(user)
    )


def _open(sockets: tuple[WebSocketTestSession, ...]) -> None:
    for socket in sockets:
        assert socket.receive_json()["type"] == "connected"


def test_dm_end_gives_each_socket_one_session_ended_frame(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _session(client_gw, client_sess, start=True)

    with (
        _connect(client_gw, session_id, DM) as dm_ws,
        _connect(client_gw, session_id, PLAYER) as pws,
    ):
        _open((dm_ws, pws))
        ended = client_gw.post(f"/api/v1/sessions/{session_id}/end", headers=bearer(DM))
        assert ended.status_code == 200, ended.text
        expected = {"type": "session_ended", "sessionId": session_id, "status": "ended"}
        assert dm_ws.receive_json() == expected
        assert pws.receive_json() == expected

    state = client_gw.get(f"/api/v1/sessions/{session_id}", headers=bearer(DM))
    assert state.json()["status"] == "ended"


def test_a_player_end_is_refused_and_sends_no_frame(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _session(client_gw, client_sess, start=True)

    with _connect(client_gw, session_id, DM) as dm_ws:
        _open((dm_ws,))
        refused = client_gw.post(f"/api/v1/sessions/{session_id}/end", headers=bearer(PLAYER))
        assert refused.status_code == 403, refused.text
        # The next frame is the turn advance, so the refused end sent nothing.
        advanced = client_gw.post(
            f"/api/v1/sessions/{session_id}/turns/advance", headers=bearer(DM)
        )
        assert advanced.status_code == 200, advanced.text
        assert dm_ws.receive_json()["type"] == "turn_advanced"


def test_an_end_from_lobby_is_refused_and_sends_no_frame(
    client_gw: TestClient, client_sess: TestClient
) -> None:
    session_id = _session(client_gw, client_sess, start=False)

    with _connect(client_gw, session_id, DM) as dm_ws:
        _open((dm_ws,))
        refused = client_gw.post(f"/api/v1/sessions/{session_id}/end", headers=bearer(DM))
        assert refused.status_code == 400, refused.text
        # The next frame is the start, so the refused end sent nothing.
        started = client_gw.post(f"/api/v1/sessions/{session_id}/start", headers=bearer(DM))
        assert started.status_code == 200, started.text
        assert dm_ws.receive_json() == {
            "type": "session_started",
            "sessionId": session_id,
            "status": "active",
        }
