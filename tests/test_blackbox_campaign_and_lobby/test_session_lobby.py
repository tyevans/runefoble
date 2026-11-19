"""Blackbox frontdoor tests for Session Lobby Gathering, Readiness, and Launch (US-0065).

Governed by ADR-0001, ADR-0003, ADR-0006, TASK-0910, and Hard Invariants 6 and 7. A client
cannot send `session_started`. Only the gateway start route sends it, after the owner moves the
session from `lobby` to `active`.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from game_session.shared.streams import STREAM_SESSION
from gateway_api.main import app as gateway_app
from gateway_api.proxy import UPSTREAM_INVALID_DETAIL

from tests.helpers.campaign_setup import create_owned_campaign
from tests.helpers.live_services import serve
from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_session_lobby_readiness_and_ai_stand_in(client_sess: TestClient) -> None:
    """Verify players assembling in lobby, readiness presence, and absent stand-in toggle."""
    char_valeros_id, char_kyra_id = uuid4(), uuid4()
    campaign_id = create_owned_campaign(client_sess)
    _seat_players(client_sess, campaign_id, ["player_marcus", "player_sarah"])

    sess_res = client_sess.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Session 15"},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]
    assert sess_res.json()["status"] == "lobby"

    p_m = {
        "character_id": str(char_valeros_id),
        "character_name": "Valeros",
        "character_class": "Fighter",
    }
    join_m = client_sess.post(
        f"/api/v1/sessions/{session_id}/join", json=p_m, headers=bearer("player_marcus")
    )
    assert join_m.status_code == 200
    m_part = join_m.json()["participants"]["player_marcus"]
    assert m_part["is_present"] is True and m_part["is_stand_in_active"] is False

    p_s = {
        "character_id": str(char_kyra_id),
        "character_name": "Kyra",
        "character_class": "Cleric",
    }
    joined_s = client_sess.post(
        f"/api/v1/sessions/{session_id}/join", json=p_s, headers=bearer("player_sarah")
    )
    assert joined_s.status_code == 200

    leave_s = client_sess.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"reason": "absent"},
        headers=bearer("player_sarah"),
    )
    assert leave_s.status_code == 200
    s_part = leave_s.json()["participants"]["player_sarah"]
    assert s_part["is_present"] is False and s_part["is_stand_in_active"] is True

    state = client_sess.get(f"/api/v1/sessions/{session_id}").json()
    assert state["status"] == "lobby" and len(state["participants"]) == 2
    assert state["participants"]["player_marcus"]["is_present"] is True
    assert state["participants"]["player_sarah"]["is_stand_in_active"] is True


def test_session_lobby_launch_transition_and_events(
    mock_bus, client_gw: TestClient, client_sess: TestClient, trusted_ws_issuer
) -> None:
    """Verify DM triggering Launch Session transitions state and emits events."""
    mock_redis = mock_bus
    headers_dm = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm_evelyn')}"}
    headers_stranger = {"Authorization": f"Bearer {trusted_ws_issuer.mint('stranger_bob')}"}

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Launch Arena"}, headers=headers_dm
    )
    camp_id = camp_res.json()["id"]

    create_res = client_sess.post(
        f"/api/v1/campaigns/{camp_id}/sessions",
        json={"title": "Launch Session"},
        headers=headers_dm,
    )
    assert create_res.status_code == 201, create_res.text
    session_id = create_res.json()["id"]
    _seat_players(client_sess, camp_id, ["player_marcus"], owner=headers_dm)

    unauth = client_gw.post(f"/api/v1/sessions/{session_id}/start", headers=headers_stranger)
    assert unauth.status_code == 403
    joined = client_sess.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": str(uuid4()),
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
        headers=bearer("player_marcus"),
    )
    assert joined.status_code == 200, joined.text

    path = f"/ws/session/{session_id}"
    with (
        client_gw.websocket_connect(path, subprotocols=ws_subprotocols("dm_evelyn")) as ws,
        client_gw.websocket_connect(path, subprotocols=ws_subprotocols("player_marcus")) as pws,
    ):
        assert ws.receive_json()["type"] == "connected"
        assert pws.receive_json()["type"] == "connected"

        pws.send_json(
            {"type": "session_started", "campaignId": "camp-elsewhere", "sessionId": session_id}
        )
        assert pws.receive_json()["code"] == "UNKNOWN_FRAME"
        assert _session_status(client_gw, session_id, headers_dm) == "lobby"

        gw_launch = client_gw.post(f"/api/v1/sessions/{session_id}/start", headers=headers_dm)
        assert gw_launch.status_code == 200 and gw_launch.json()["status"] == "active"
        # The next DM frame is the gateway frame, so the forged frame never reached the DM.
        for socket in (ws, pws):
            msg = socket.receive_json()
            assert msg == {"type": "session_started", "sessionId": session_id, "status": "active"}

    active_state = client_sess.get(f"/api/v1/sessions/{session_id}", headers=headers_dm).json()
    assert active_state["status"] == "active" and active_state["current_turn"] == 1
    assert active_state["active_character_id"] is not None

    session_events = mock_redis.streams.get(STREAM_SESSION, [])
    assert any("runefoble.events.session.started" in str(evt) for evt in session_events)


def test_a_start_reply_without_status_is_a_502_not_a_crash(trusted_ws_issuer) -> None:
    """An owner start reply that breaks the contract gives 502 with a fixed detail (TASK-0910)."""
    owner = FastAPI()

    @owner.post("/api/v1/sessions/{session_id}/start")
    async def start(session_id: str) -> dict[str, str]:
        return {"id": session_id}

    with (
        serve(owner) as owner_url,
        pytest.MonkeyPatch.context() as env,
    ):
        env.setenv("RUNEFOBLE_GAME_SESSION_URL", owner_url)
        with TestClient(gateway_app, raise_server_exceptions=False) as gateway:
            reply = gateway.post("/api/v1/sessions/s-1/start", headers=bearer("dm_evelyn"))

    assert reply.status_code == 502
    assert reply.json() == {"detail": UPSTREAM_INVALID_DETAIL}


def _session_status(client: TestClient, session_id: str, headers: dict[str, str]) -> str:
    """Read the session status through the gateway session route."""
    read = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert read.status_code == 200, read.text
    return read.json()["status"]


def _seat_players(
    client, campaign_id: str, players: list[str], owner: dict[str, str] | None = None
) -> None:
    """Invite each player into the campaign and redeem the invite as that player."""
    for player in players:
        invite = client.post(
            f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=owner
        )
        assert invite.status_code == 201, invite.text
        redeemed = client.post(
            "/api/v1/campaigns/join",
            json={"invite_token": invite.json()["token"]},
            headers=bearer(player),
        )
        assert redeemed.status_code == 200, redeemed.text
