"""Blackbox frontdoor test suite for Campaign Management and Session Lobby.

Part of TASK-0215 / PRD-0023 / US-0063 / US-0064 / US-0065.
Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (<350 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from character_sheet.dependencies import set_spicedb_client as set_char_spicedb
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_SESSION,
    set_event_bus,
)
from game_session.dependencies import (
    set_spicedb_client as set_sess_spicedb,
)
from game_session.main import app as session_app
from gateway_api.auth import get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app
from runefoble_platform.consumer_group import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

client_gw = TestClient(gateway_app)
client_sess = TestClient(session_app)
client_char = TestClient(character_app)


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset gateway campaign store and configure isolated event bus and shared SpiceDB."""
    campaign_store.reset()
    spicedb = get_spicedb_client()
    set_char_spicedb(spicedb)
    set_sess_spicedb(spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield mock_redis
    set_event_bus(None)


# ---------------------------------------------------------------------------
# 1. Campaign Creation, Zanzibar Ownership, and Access Control (US-0063)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_campaign_creation_ownership_and_access_control():
    """Verify campaign creation assigns Zanzibar owner relation and guards access."""
    headers_evelyn = {"X-User-Id": "dm_evelyn"}
    spicedb = get_spicedb_client()

    # 1. Evelyn creates campaign via public frontdoor POST /api/v1/campaigns
    res = client_gw.post(
        "/api/v1/campaigns",
        json={"title": "Shadows of Drakkenheim", "setting": "Gothic Fantasy"},
        headers=headers_evelyn,
    )
    assert res.status_code == 201
    camp = res.json()
    campaign_id = camp["id"]
    assert camp["title"] == "Shadows of Drakkenheim"
    assert camp["role"] == "owner"
    assert camp["owner_id"] == "dm_evelyn"

    # 2. Evelyn is granted owner, manage, run_session, and view in SpiceDB Zanzibar
    assert await spicedb.check_permission("campaign", campaign_id, "manage", "user", "dm_evelyn")
    assert await spicedb.check_permission(
        "campaign", campaign_id, "run_session", "user", "dm_evelyn"
    )
    assert await spicedb.check_permission("campaign", campaign_id, "view", "user", "dm_evelyn")

    # 3. Evelyn can inspect details; unauthorized stranger receives 403 Forbidden
    assert (
        client_gw.get(f"/api/v1/campaigns/{campaign_id}", headers=headers_evelyn).status_code == 200
    )
    res_stranger = client_gw.get(
        f"/api/v1/campaigns/{campaign_id}", headers={"X-User-Id": "stranger_bob"}
    )
    assert res_stranger.status_code == 403
    assert res_stranger.json()["detail"]["error"] == "permission_denied"


# ---------------------------------------------------------------------------
# 2. Campaign Invites, Redemption, and Zanzibar Role Assignment (US-0063)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_campaign_invite_redemption_and_role_assignment():
    """Verify shareable invite token lifecycle, redemption, and Zanzibar role sync."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}
    spicedb = get_spicedb_client()

    # Setup: Create campaign
    create_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Star-Eater Odyssey"}, headers=headers_dm
    )
    camp_id = create_res.json()["id"]

    # 1. Non-manager is forbidden from generating invites
    res_unauth = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers={"X-User-Id": "stranger_bob"},
    )
    assert res_unauth.status_code == 403

    # 2. DM generates shareable player invite token
    invite_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player", "max_uses": 2, "expires_in_hours": 48},
        headers=headers_dm,
    )
    assert invite_res.status_code == 201
    token = invite_res.json()["token"]

    # 3. Marcus redeems invite token via POST /api/v1/campaigns/join
    join_res = client_gw.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=headers_marcus
    )
    assert join_res.status_code == 200
    assert join_res.json()["status"] == "joined"
    assert join_res.json()["role"] == "player"

    # 4. DM updates/assigns Zanzibar role tuple explicitly
    role_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": "player_marcus", "role": "player"},
        headers=headers_dm,
    )
    assert role_res.status_code == 200

    # 5. Member roster listing reflects both members and roles
    members_res = client_gw.get(f"/api/v1/campaigns/{camp_id}/members", headers=headers_marcus)
    assert members_res.status_code == 200
    roles_map = {m["user_id"]: m["role"] for m in members_res.json()}
    assert roles_map.get("dm_evelyn") == "owner"
    assert roles_map.get("player_marcus") == "player"

    # 6. Verify Zanzibar permissions: Marcus has play & view, but not manage
    assert await spicedb.check_permission("campaign", camp_id, "play", "user", "player_marcus")
    assert await spicedb.check_permission("campaign", camp_id, "view", "user", "player_marcus")
    assert not await spicedb.check_permission(
        "campaign", camp_id, "manage", "user", "player_marcus"
    )


# ---------------------------------------------------------------------------
# 3. Character Creation and Campaign Party Assignment (US-0064)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_character_creation_and_party_assignment():
    """Verify character creation, SpiceDB ownership, and campaign party binding."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}
    spicedb = get_spicedb_client()

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Tomb of the Star-Eater"}, headers=headers_dm
    )
    camp_id = camp_res.json()["id"]

    # 1. Marcus creates character "Valeros" via POST /api/v1/characters
    char_res = client_char.post(
        "/api/v1/characters",
        json={
            "name": "Valeros",
            "character_class": "Fighter",
            "max_hp": 45,
            "player_id": "player_marcus",
        },
        headers=headers_marcus,
    )
    assert char_res.status_code == 200
    char_data = char_res.json()
    char_id = str(char_data.get("character_id") or char_data["id"])
    assert char_data["name"] == "Valeros"
    assert char_data["max_hp"] == 45

    # 2. Verify Marcus holds owner and edit permission for the character
    assert await spicedb.check_permission("character", char_id, "edit", "user", "player_marcus")

    # 3. Marcus assigns character to campaign party via frontdoor sync API
    sync_res = client_gw.post(
        "/api/v1/auth/sync/character-ownership",
        json={"character_id": char_id, "user_id": "player_marcus", "campaign_id": camp_id},
        headers=headers_marcus,
    )
    assert sync_res.status_code == 200
    assert sync_res.json()["status"] == "ownership_bound"

    # 4. DM Evelyn now has edit & view on character via Zanzibar campaign->run_session
    assert await spicedb.check_permission("character", char_id, "edit", "user", "dm_evelyn")
    assert await spicedb.check_permission("character", char_id, "view", "user", "dm_evelyn")

    # 5. Unrelated stranger has no edit permission
    assert not await spicedb.check_permission("character", char_id, "edit", "user", "stranger_bob")


# ---------------------------------------------------------------------------
# 4. Pre-Game Lobby Gathering, Readiness, and AI Stand-In (US-0065)
# ---------------------------------------------------------------------------


def test_session_lobby_readiness_and_ai_stand_in():
    """Verify players assembling in lobby, readiness presence, and absent stand-in toggle."""
    campaign_id = uuid4()
    char_valeros_id, char_kyra_id = uuid4(), uuid4()

    # 1. DM schedules session in lobby state
    sess_res = client_sess.post(
        "/api/v1/sessions/create",
        json={
            "campaign_id": str(campaign_id),
            "title": "Session 15: Chamber of Horrors",
            "dm_id": "dm_evelyn",
        },
    )
    assert sess_res.status_code == 200
    session_data = sess_res.json()
    session_id = session_data["session_id"]
    assert session_data["status"] == "lobby"

    # 2. Marcus joins lobby with Valeros: presence is online and active
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

    # 3. Sarah joins lobby with Kyra
    p_s = {
        "player_id": "player_sarah",
        "character_id": str(char_kyra_id),
        "character_name": "Kyra",
        "character_class": "Cleric",
    }
    join_s = client_sess.post(f"/api/v1/sessions/{session_id}/join", json=p_s)
    assert join_s.status_code == 200

    # 4. Sarah indicates absence, enabling AI Stand-In toggle
    leave_s = client_sess.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"player_id": "player_sarah", "reason": "absent"},
    )
    assert leave_s.status_code == 200
    s_part = leave_s.json()["participants"]["player_sarah"]
    assert s_part["is_present"] is False and s_part["is_stand_in_active"] is True

    # 5. Public session state frontdoor shows 1 active player and 1 absent stand-in
    state = client_sess.get(f"/api/v1/sessions/{session_id}").json()
    assert state["status"] == "lobby"
    assert len(state["participants"]) == 2
    assert state["participants"]["player_marcus"]["is_present"] is True
    assert state["participants"]["player_sarah"]["is_stand_in_active"] is True


# ---------------------------------------------------------------------------
# 5. Live Launch Orchestration, Events, and WebSocket Transition (US-0065)
# ---------------------------------------------------------------------------


def test_session_lobby_launch_transition_and_events(reset_stores):
    """Verify DM triggering Launch Session transitions state and emits events."""
    mock_redis = reset_stores
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_stranger = {"X-User-Id": "stranger_bob"}

    camp_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Launch Arena"}, headers=headers_dm
    )
    camp_id = camp_res.json()["id"]

    # 1. Stranger without run_session permission is denied session launch
    assert (
        client_gw.post(f"/api/v1/sessions/{camp_id}/start", headers=headers_stranger).status_code
        == 403
    )

    # 2. Setup game session aggregate in lobby
    camp_uuid = UUID(camp_id) if len(camp_id) == 36 else uuid4()
    create_res = client_sess.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(camp_uuid), "title": "Launch Session", "dm_id": "dm_evelyn"},
    )
    session_id = create_res.json()["session_id"]
    p_join = {
        "player_id": "player_marcus",
        "character_id": str(uuid4()),
        "character_name": "Valeros",
        "character_class": "Fighter",
    }
    client_sess.post(f"/api/v1/sessions/{session_id}/join", json=p_join)

    # 3. Connect real-time WebSocket client to session stream
    with client_gw.websocket_connect(f"/ws/session/{session_id}") as ws:
        assert ws.receive_json()["type"] == "connected"

        # 4. DM triggers "Launch Session" via Gateway frontdoor
        gw_launch = client_gw.post(f"/api/v1/sessions/{camp_id}/start", headers=headers_dm)
        assert gw_launch.status_code == 200
        assert gw_launch.json()["status"] == "active"

        # 5. Connected clients receive broadcast transition message
        msg = ws.receive_json()
        assert msg["type"] == "session_started" and msg["status"] == "active"

    # 6. Backend session aggregate transitions from lobby to active and publishes domain event
    start_res = client_sess.post(f"/api/v1/sessions/{session_id}/start")
    assert start_res.status_code == 200
    active_state = start_res.json()
    assert active_state["status"] == "active"
    assert active_state["current_turn"] == 1
    assert active_state["active_character_id"] is not None

    # 7. Verify SessionStarted CloudEvent was published to Redis stream
    session_events = mock_redis.streams.get(STREAM_SESSION, [])
    assert any("SessionStarted" in str(evt) for evt in session_events)
