"""Blackbox frontdoor tests for Session Lobby Gathering, Readiness, and Launch (US-0065).

Governed by ADR-0001, ADR-0003, ADR-0006, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_SESSION


def test_session_lobby_readiness_and_ai_stand_in(client_sess: TestClient) -> None:
    """Verify players assembling in lobby, readiness presence, and absent stand-in toggle."""
    campaign_id, char_valeros_id, char_kyra_id = uuid4(), uuid4(), uuid4()

    sess_res = client_sess.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(campaign_id), "title": "Session 15", "dm_id": "dm_evelyn"},
    )
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]
    assert sess_res.json()["status"] == "lobby"

    p_m = {
        "player_id": "player_marcus",
        "character_id": str(char_valeros_id),
        "character_name": "Valeros",
        "character_class": "Fighter",
    }
    join_m = client_sess.post(f"/api/v1/sessions/{session_id}/join", json=p_m)
    assert join_m.status_code == 200
    m_part = join_m.json()["participants"]["player_marcus"]
    assert m_part["is_present"] is True and m_part["is_stand_in_active"] is False

    p_s = {
        "player_id": "player_sarah",
        "character_id": str(char_kyra_id),
        "character_name": "Kyra",
        "character_class": "Cleric",
    }
    assert client_sess.post(f"/api/v1/sessions/{session_id}/join", json=p_s).status_code == 200

    leave_s = client_sess.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"player_id": "player_sarah", "reason": "absent"},
    )
    assert leave_s.status_code == 200
    s_part = leave_s.json()["participants"]["player_sarah"]
    assert s_part["is_present"] is False and s_part["is_stand_in_active"] is True

    state = client_sess.get(f"/api/v1/sessions/{session_id}").json()
    assert state["status"] == "lobby" and len(state["participants"]) == 2
    assert state["participants"]["player_marcus"]["is_present"] is True
    assert state["participants"]["player_sarah"]["is_stand_in_active"] is True


def test_session_lobby_launch_transition_and_events(
    reset_stores, client_gw: TestClient, client_sess: TestClient
) -> None:
    """Verify DM triggering Launch Session transitions state and emits events."""
    mock_redis = reset_stores
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_stranger = {"X-User-Id": "stranger_bob"}

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Launch Arena"}, headers=headers_dm
    )
    camp_id = camp_res.json()["id"]

    unauth = client_gw.post(f"/api/v1/sessions/{camp_id}/start", headers=headers_stranger)
    assert unauth.status_code == 403

    camp_uuid = UUID(camp_id) if len(camp_id) == 36 else uuid4()
    create_res = client_sess.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(camp_uuid), "title": "Launch Session", "dm_id": "dm_evelyn"},
    )
    session_id = create_res.json()["session_id"]
    client_sess.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "player_marcus",
            "character_id": str(uuid4()),
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
    )

    with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws:
        assert ws.receive_json()["type"] == "connected"
        gw_launch = client_gw.post(f"/api/v1/sessions/{camp_id}/start", headers=headers_dm)
        assert gw_launch.status_code == 200 and gw_launch.json()["status"] == "active"
        msg = ws.receive_json()
        assert msg["type"] == "session_started" and msg["status"] == "active"

    start_res = client_sess.post(f"/api/v1/sessions/{session_id}/start")
    assert start_res.status_code == 200
    active_state = start_res.json()
    assert active_state["status"] == "active" and active_state["current_turn"] == 1
    assert active_state["active_character_id"] is not None

    session_events = mock_redis.streams.get(STREAM_SESSION, [])
    assert any("SessionStarted" in str(evt) for evt in session_events)
