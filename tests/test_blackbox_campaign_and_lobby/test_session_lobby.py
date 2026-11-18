"""Blackbox frontdoor tests for Session Lobby Gathering, Readiness, and Launch (US-0065).

Governed by ADR-0001, ADR-0003, ADR-0006, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_SESSION

from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_session_lobby_readiness_and_ai_stand_in(client_sess: TestClient) -> None:
    """Verify players assembling in lobby, readiness presence, and absent stand-in toggle."""
    char_valeros_id, char_kyra_id = uuid4(), uuid4()
    campaign_id = _owned_campaign(client_sess)
    _seat_players(client_sess, campaign_id, ["player_marcus", "player_sarah"])

    sess_res = client_sess.post(
        "/api/v1/sessions/create",
        json={
            "campaign_id": campaign_id,
            "title": "Session 15",
            "dm_id": "dm_evelyn",
        },
    )
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]
    assert sess_res.json()["status"] == "lobby"

    p_m = {
        "character_id": str(char_valeros_id),
        "character_name": "Valeros",
        "character_class": "Fighter",
    }
    join_m = client_sess.post(
        f"/api/v1/sessions/{session_id}/join", json=p_m, headers=_bearer("player_marcus")
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
        f"/api/v1/sessions/{session_id}/join", json=p_s, headers=_bearer("player_sarah")
    )
    assert joined_s.status_code == 200

    leave_s = client_sess.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"reason": "absent"},
        headers=_bearer("player_sarah"),
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
        "/api/v1/sessions/create",
        json={"campaign_id": camp_id, "title": "Launch Session", "dm_id": "dm_evelyn"},
        headers=headers_dm,
    )
    assert create_res.status_code == 200, create_res.text
    session_id = create_res.json()["session_id"]
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
        headers=_bearer("player_marcus"),
    )
    assert joined.status_code == 200, joined.text

    with client_gw.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols("dm_evelyn")
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
        gw_launch = client_gw.post(f"/api/v1/sessions/{session_id}/start", headers=headers_dm)
        assert gw_launch.status_code == 200 and gw_launch.json()["status"] == "active"
        msg = ws.receive_json()
        assert msg["type"] == "session_started" and msg["status"] == "active"

    active_state = client_sess.get(f"/api/v1/sessions/{session_id}", headers=headers_dm).json()
    assert active_state["status"] == "active" and active_state["current_turn"] == 1
    assert active_state["active_character_id"] is not None

    session_events = mock_redis.streams.get(STREAM_SESSION, [])
    assert any("SessionStarted" in str(evt) for evt in session_events)


def _owned_campaign(client) -> str:
    """Create a campaign as the calling user, so that the caller can run sessions in it."""
    res = client.post("/api/v1/campaigns", json={"title": "Owned Campaign"})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


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
            headers=_bearer(player),
        )
        assert redeemed.status_code == 200, redeemed.text
